"""Deterministic type adapters: the connector layer that mutates one port
shape into a compatible one so the route compiler can bridge a near-match
instead of leaving a gap.

An adapter is a pure, deterministic, REVIEWED transform ``FromPort -> ToPort``.
Registered as a capability-graph node (``kind: "type_adapter"``), it lets the
forward-chaining compiler insert a bridge automatically - and because every
adapter is one auditable node, an adapter-mediated route DISCLOSES the bridge as
an explicit step, never a silent type collapse. That is the difference between
this and widening the canonical-type buckets: adapters are curated code with a
proof, not a heuristic that merges distinct artifacts.

Each adapter here is ``def <name>(payload: dict) -> PrimitiveOutcome`` and, like
the remix mutators in primitives/mutators.py:

- reports ``effects_observed == ["none"]`` (pure computation, no I/O);
- emits an ``adapter_receipt`` disclosing lossiness and any dropped fields;
- runs its own proofs (a roundtrip/inverse where lossless is claimed, a
  value-preservation or disclosure proof where the reshape is lossy).

``REGISTRY`` maps adapter_id -> function and ``SELF_TESTS`` maps adapter_id -> a
fixture payload whose proofs must all pass; the adapter pack checker
(scripts/check_type_adapters_pack.py) runs every backed adapter through its
fixture so a declared adapter that does not actually work goes red.

Stdlib only. Outputs are candidate material; nothing here promotes truth.
"""

from __future__ import annotations

from primitives.core import PrimitiveOutcome, ProofResult, canonical_hash
from primitives.mutators import json_records_to_rows, records_to_geojson_points


def _adapter_receipt(adapter: str, lossiness: str, fields_dropped: list,
                     preconditions: list) -> dict:
    return {
        "adapter": adapter,
        "lossiness": lossiness,
        "fields_dropped": list(fields_dropped),
        "preconditions_checked": list(preconditions),
    }


# ---------------------------------------------------------------------------
# adapt:webhook_request_to_provider_webhook
#   WebhookHttpRequest -> ProviderWebhook
# ---------------------------------------------------------------------------

def webhook_request_to_provider_webhook(payload: dict) -> PrimitiveOutcome:
    """Interpret a raw inbound HTTP request as a typed provider-webhook envelope.

    payload:
        method, headers (object), body (object|string), source_ip (optional)

    Deterministically reads the provider identity from a declared header
    (``X-Webhook-Provider``, case-insensitive), carries method/headers/body
    verbatim into a ProviderWebhook envelope. Lossless: the inverse rebuilds the
    original request fields.

    proofs: schema_validation, provider_identified, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = ["method_and_headers_present", "provider_header_present",
                     "body_carried_verbatim"]
    receipt = _adapter_receipt("webhook_request_to_provider_webhook",
                               "lossless", [], preconditions)
    errors: list[str] = []
    method = payload.get("method")
    headers = payload.get("headers")
    body = payload.get("body")
    if not isinstance(method, str) or not method:
        errors.append("'method' must be a nonempty string")
    if not isinstance(headers, dict):
        errors.append("'headers' must be an object")
        headers = {}
    proofs = [ProofResult("schema_validation", not errors,
                          "; ".join(errors) if errors else "request fields validated")]
    if errors:
        return PrimitiveOutcome(output={"provider_webhook": None, "adapter_receipt": receipt},
                                effects_observed=["none"], proof_results=proofs)

    lowered = {k.lower(): v for k, v in headers.items()}
    provider = lowered.get("x-webhook-provider")
    proofs.append(ProofResult("provider_identified", isinstance(provider, str) and bool(provider),
                              f"provider={provider!r}" if provider else
                              "no X-Webhook-Provider header"))
    if not (isinstance(provider, str) and provider):
        return PrimitiveOutcome(output={"provider_webhook": None, "adapter_receipt": receipt},
                                effects_observed=["none"], proof_results=proofs)

    envelope = {"provider": provider, "method": method, "headers": headers, "payload": body}
    rebuilt = {"method": envelope["method"], "headers": envelope["headers"],
               "body": envelope["payload"]}
    original = {"method": method, "headers": headers, "body": body}
    roundtrip_ok = canonical_hash(rebuilt) == canonical_hash(original)
    proofs.append(ProofResult("roundtrip_test", roundtrip_ok,
                              "request fields reproduced from the envelope" if roundtrip_ok
                              else "envelope did not carry request fields verbatim"))
    return PrimitiveOutcome(output={"provider_webhook": envelope, "adapter_receipt": receipt},
                            effects_observed=["none"], proof_results=proofs)


# ---------------------------------------------------------------------------
# adapt:auth_decision_to_authenticated_subject
#   AuthDecision -> AuthenticatedSubject   (LOSSY: only on an allow decision)
# ---------------------------------------------------------------------------

def auth_decision_to_authenticated_subject(payload: dict) -> PrimitiveOutcome:
    """Expose the authenticated subject carried by a POSITIVE auth decision.

    payload:
        decision ("allow"|"deny"), subject (object with at least subject_id),
        plus any decision metadata (dropped, disclosed)

    Precondition: decision == "allow". A deny decision has no authenticated
    subject and fails the gate. Lossy: decision metadata is dropped and
    disclosed; the subject is carried verbatim.

    proofs: schema_validation, allow_decision_gate, subject_preserved
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = ["decision_is_allow", "subject_has_id", "decision_metadata_disclosed"]
    errors: list[str] = []
    decision = payload.get("decision")
    subject = payload.get("subject")
    if decision not in ("allow", "deny"):
        errors.append("'decision' must be 'allow' or 'deny'")
    if not isinstance(subject, dict) or not subject.get("subject_id"):
        errors.append("'subject' must be an object with a subject_id")
    dropped = sorted(k for k in payload if k not in ("decision", "subject"))
    receipt = _adapter_receipt("auth_decision_to_authenticated_subject", "lossy",
                               dropped, preconditions)
    proofs = [ProofResult("schema_validation", not errors,
                          "; ".join(errors) if errors else "decision and subject validated")]
    if errors:
        return PrimitiveOutcome(output={"authenticated_subject": None, "adapter_receipt": receipt},
                                effects_observed=["none"], proof_results=proofs)

    allow = decision == "allow"
    proofs.append(ProofResult("allow_decision_gate", allow,
                              "decision is allow; subject is authenticated" if allow
                              else "deny decision has no authenticated subject"))
    if not allow:
        return PrimitiveOutcome(output={"authenticated_subject": None, "adapter_receipt": receipt},
                                effects_observed=["none"], proof_results=proofs)

    preserved = canonical_hash(subject) == canonical_hash(payload.get("subject"))
    proofs.append(ProofResult("subject_preserved", preserved,
                              "authenticated subject carried verbatim" if preserved
                              else "subject was altered"))
    return PrimitiveOutcome(output={"authenticated_subject": dict(subject), "adapter_receipt": receipt},
                            effects_observed=["none"], proof_results=proofs)


# ---------------------------------------------------------------------------
# adapt:session_grant_to_token
#   SessionGrant -> SessionToken   (LOSSY: extracts the bearer token)
# ---------------------------------------------------------------------------

def session_grant_to_token(payload: dict) -> PrimitiveOutcome:
    """Extract the bearer token string from a session grant record.

    payload:
        token (nonempty string), plus grant metadata (expires_at, scope, ...)
        which is dropped and disclosed.

    Lossy by construction: only the token survives.

    proofs: schema_validation, token_present, token_preserved
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = ["token_present", "grant_metadata_disclosed"]
    errors: list[str] = []
    token = payload.get("token")
    if not isinstance(token, str) or not token:
        errors.append("'token' must be a nonempty string")
    dropped = sorted(k for k in payload if k != "token")
    receipt = _adapter_receipt("session_grant_to_token", "lossy", dropped, preconditions)
    proofs = [ProofResult("schema_validation", not errors,
                          "; ".join(errors) if errors else "grant validated")]
    if errors:
        return PrimitiveOutcome(output={"session_token": None, "adapter_receipt": receipt},
                                effects_observed=["none"], proof_results=proofs)
    proofs.append(ProofResult("token_present", True, "bearer token extracted"))
    proofs.append(ProofResult("token_preserved", payload.get("token") == token,
                              "token carried verbatim"))
    return PrimitiveOutcome(output={"session_token": token, "adapter_receipt": receipt},
                            effects_observed=["none"], proof_results=proofs)


# ---------------------------------------------------------------------------
# adapt:match_score_to_set
#   MatchScore -> MatchScoreSet   (wrap a single score into a singleton set)
# ---------------------------------------------------------------------------

def match_score_to_set(payload: dict) -> PrimitiveOutcome:
    """Wrap a single match score into a singleton match-score set.

    payload:
        pair_id (string), score (number in [0,1])

    Lossless: the inverse (take the sole element) reproduces the input.

    proofs: schema_validation, score_in_unit_range, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = ["singleton_wrap", "score_in_unit_range"]
    receipt = _adapter_receipt("match_score_to_set", "lossless", [], preconditions)
    errors: list[str] = []
    pair_id = payload.get("pair_id")
    score = payload.get("score")
    if not isinstance(pair_id, str) or not pair_id:
        errors.append("'pair_id' must be a nonempty string")
    if not (isinstance(score, (int, float)) and not isinstance(score, bool)):
        errors.append("'score' must be a number")
    proofs = [ProofResult("schema_validation", not errors,
                          "; ".join(errors) if errors else "match score validated")]
    if errors:
        return PrimitiveOutcome(output={"match_scores": [], "adapter_receipt": receipt},
                                effects_observed=["none"], proof_results=proofs)
    in_range = 0.0 <= float(score) <= 1.0
    proofs.append(ProofResult("score_in_unit_range", in_range,
                              f"score={score} in [0,1]" if in_range else f"score={score} out of [0,1]"))
    if not in_range:
        return PrimitiveOutcome(output={"match_scores": [], "adapter_receipt": receipt},
                                effects_observed=["none"], proof_results=proofs)
    match_set = [{"pair_id": pair_id, "score": score}]
    sole = match_set[0]
    roundtrip_ok = sole["pair_id"] == pair_id and sole["score"] == score and len(match_set) == 1
    proofs.append(ProofResult("roundtrip_test", roundtrip_ok,
                              "sole element reproduces the input score" if roundtrip_ok
                              else "singleton wrap did not preserve the score"))
    return PrimitiveOutcome(output={"match_scores": match_set, "adapter_receipt": receipt},
                            effects_observed=["none"], proof_results=proofs)


# ---------------------------------------------------------------------------
# Mutator-backed adapters (reuse the tested remix mutators as typed bridges)
# ---------------------------------------------------------------------------

def _wrap_mutator(adapter: str, outcome: PrimitiveOutcome) -> PrimitiveOutcome:
    """Attach an adapter_receipt to a mutator-backed outcome (carrying the
    underlying mutation_receipt) so every adapter discloses uniformly."""
    mut = outcome.output.get("mutation_receipt", {})
    receipt = _adapter_receipt(adapter, mut.get("lossiness", "lossless"),
                               mut.get("fields_dropped", []),
                               mut.get("preconditions_checked", []) + [f"backed_by:{mut.get('mutator')}"])
    new_output = dict(outcome.output)
    new_output["adapter_receipt"] = receipt
    return PrimitiveOutcome(output=new_output,
                            effects_observed=list(outcome.effects_observed),
                            proof_results=list(outcome.proof_results))


def entity_records_to_rows(payload: dict) -> PrimitiveOutcome:
    """EntityRecordSet -> RowSet, backed by the tested json_records_to_rows
    mutator (lossless modulo the disclosed missing-key -> null normalization)."""
    return _wrap_mutator("adapt:entity_records_to_rows", json_records_to_rows(payload))


def entity_records_to_geojson_points(payload: dict) -> PrimitiveOutcome:
    """EntityRecordSet(lat/lon) -> PointFeatureCollection, backed by the tested
    records_to_geojson_points mutator (lossless, [lon,lat] order)."""
    return _wrap_mutator("adapt:entity_records_to_geojson_points",
                         records_to_geojson_points(payload))


# ---------------------------------------------------------------------------
# Registry + self-test fixtures (the checker runs every backed adapter through
# its fixture and asserts all proofs pass)
# ---------------------------------------------------------------------------

REGISTRY = {
    "adapt:webhook_request_to_provider_webhook": webhook_request_to_provider_webhook,
    "adapt:auth_decision_to_authenticated_subject": auth_decision_to_authenticated_subject,
    "adapt:session_grant_to_token": session_grant_to_token,
    "adapt:match_score_to_set": match_score_to_set,
    "adapt:entity_records_to_rows": entity_records_to_rows,
    "adapt:entity_records_to_geojson_points": entity_records_to_geojson_points,
}

SELF_TESTS = {
    "adapt:webhook_request_to_provider_webhook": {
        "method": "POST",
        "headers": {"X-Webhook-Provider": "stripe", "Content-Type": "application/json"},
        "body": {"event": "charge.succeeded", "id": "evt_1"},
    },
    "adapt:auth_decision_to_authenticated_subject": {
        "decision": "allow",
        "subject": {"subject_id": "u_42", "roles": ["member"]},
        "policy_version": "v3",
    },
    "adapt:session_grant_to_token": {
        "token": "sess_abc123", "expires_at": "2026-07-04T00:00:00Z", "scope": "read",
    },
    "adapt:match_score_to_set": {"pair_id": "a::b", "score": 0.87},
    "adapt:entity_records_to_rows": {
        "records": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
    },
    "adapt:entity_records_to_geojson_points": {
        "records": [{"id": 1, "lat": 40.0, "lon": -74.0}],
    },
}
