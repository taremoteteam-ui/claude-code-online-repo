"""Typed edge / port model for the primitive capability graph.

A primitive's contract is a compact edge string: ``TypeA+TypeB+Policy`` on the
input side, ``TypeX+Receipt`` on the output side. To COMPILE a graph of
primitives by their edges alone - the whole point of the bank - those ports
need a shared type vocabulary so an upstream output can satisfy a downstream
input without reading either primitive's internals.

This module gives every port three deterministic facts:
  - role:  data | config | receipt
      config ports (Policy/Spec/Context/Weights/Preference) are supplied by
      the compile REQUEST, not produced upstream, so they never block
      composition. receipt ports are evidence outputs. data ports are the
      artifacts that must be produced upstream or provided as inputs.
  - canonical_type: a curated, conservative capability type. Many concrete
      ports (HRSASiteRecordSet, TrainingProviderRecordSet, ProviderCandidateSet)
      share the canonical type RecordCollection, so a producer of one can
      satisfy a consumer of another at TYPED tier. Ports with no recognized
      head map to their own name, so they only ever match EXACTLY.

The compiler composes on canonical_type and labels each connection exact vs
typed, so every type-based hop is auditable, never a hidden guess.

Stdlib only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Config-port suffixes: supplied by the request, never produced upstream.
_CONFIG_SUFFIXES = ("Policy", "Spec", "Context", "Weights", "Preference",
                    "Config", "Settings")
# Receipt/evidence-port suffixes.
_RECEIPT_SUFFIXES = ("Receipt", "Report", "Verdict", "Digest", "Manifest",
                     "Decision", "Scorecard")

# Curated, AUDITABLE port-type synonyms. A port's canonical type is its own
# NAME unless it appears here - so composition is exact by default and never
# collapses genuinely-distinct artifacts (a MapArtifact is not a
# MockServerArtifact). Each entry below is a REVIEWED equivalence: distinct
# port names that denote a substitutable artifact shape, so an upstream
# producer of one may satisfy a downstream consumer of another. Expanding this
# map is promotion-gated review work, not a silent heuristic - which is exactly
# why the compiler labels every non-exact hop "typed" and every gap surfaces a
# normalization candidate.
_SYNONYM_MAP: dict[str, str] = {
    # A raw set of entity records that entity resolution can consume,
    # regardless of which source produced it.
    "RawEntityRecordSet": "EntityRecordSet",
    "HRSASiteRecordSet": "EntityRecordSet",
    "TrainingProviderRecordSet": "EntityRecordSet",
    "InstitutionProgramRecordSet": "EntityRecordSet",
    "PlaceRecordSet": "EntityRecordSet",
    "OSMPOIRecordSet": "EntityRecordSet",
    "SocrataRecordSet": "EntityRecordSet",
    "FeatureRecordSet": "EntityRecordSet",
    "ProviderCandidateSet": "EntityRecordSet",
    "StandardizedRecordSet": "EntityRecordSet",
    # A tabular dataset sample any profiler/validator can fingerprint.
    "DatasetSample": "TabularDataset",
    "InputTable": "TabularDataset",
    "SourceTable": "TabularDataset",
    "RowSet": "TabularDataset",
    # A JSON object IS a JSON document - same shape, no transform needed.
    "JsonObject": "JsonDocument",
    # An inbound login attempt carries exactly the login credential a verifier
    # consumes; substitutable with no reshape.
    "LoginAttempt": "LoginCredential",
}

_ROLE_DATA = "data"
_ROLE_CONFIG = "config"
_ROLE_RECEIPT = "receipt"


@dataclass(frozen=True)
class Port:
    name: str
    role: str            # data | config | receipt
    canonical_type: str  # capability type used for composition


def port_role(name: str) -> str:
    if name.endswith(_CONFIG_SUFFIXES):
        return _ROLE_CONFIG
    if name.endswith(_RECEIPT_SUFFIXES):
        return _ROLE_RECEIPT
    return _ROLE_DATA


def canonical_type(name: str) -> str:
    """Conservative: a port's canonical type is its own name unless a REVIEWED
    synonym says otherwise. No lossy suffix buckets - distinct artifacts never
    silently merge."""
    return _SYNONYM_MAP.get(name, name)


def parse_edge(edge: str) -> list[Port]:
    """Split ``A+B+C`` into typed ports. Tolerates empty/whitespace."""
    ports: list[Port] = []
    for raw in edge.split("+"):
        tok = raw.strip()
        if not tok or not re.match(r"^[A-Za-z0-9]+$", tok):
            continue
        ports.append(Port(tok, port_role(tok), canonical_type(tok)))
    return ports


def required_input_ports(input_edge: str) -> list[Port]:
    """Data + receipt ports a primitive needs from upstream (config excluded)."""
    return [p for p in parse_edge(input_edge) if p.role != _ROLE_CONFIG]


def config_ports(input_edge: str) -> list[Port]:
    return [p for p in parse_edge(input_edge) if p.role == _ROLE_CONFIG]


def output_ports(output_edge: str) -> list[Port]:
    return parse_edge(output_edge)
