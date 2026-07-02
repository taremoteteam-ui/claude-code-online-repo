"""Entity normalization and deduplication primitive for place records.

Normalizes place records (name, address, phone, zip), blocks candidate
pairs by (zip5, first name character), scores pairs with token-set
Jaccard and Jaro-Winkler name similarity plus haversine distance, and
clusters matches with union-find into canonical entities.

Pure and stdlib-only: no I/O, no network, no side effects. Output is
candidate material; nothing here promotes truth.
"""

from __future__ import annotations

import hashlib
import math
import re

from primitives.core import PrimitiveOutcome, ProofResult

MATCH_DECISION_CAP = 500

# Legal-form suffix tokens stripped from the tail of normalized names.
_LEGAL_SUFFIXES = {
    "INC", "INCORPORATED", "LLC", "LLP", "LP", "LTD", "LIMITED",
    "CORP", "CORPORATION", "CO", "COMPANY", "PLLC", "PC", "PA",
}

# Token-level rewrites applied to normalized name tokens.
_NAME_TOKEN_MAP = {
    "SAINT": "ST",
    "CENTER": "CTR",
    "CENTRE": "CTR",
    "MOUNT": "MT",
    "FORT": "FT",
    "ASSOCIATES": "ASSOC",
    "DEPARTMENT": "DEPT",
}

# USPS-style abbreviations applied to normalized address tokens.
_ADDRESS_TOKEN_MAP = {
    "STREET": "ST",
    "AVENUE": "AVE",
    "ROAD": "RD",
    "DRIVE": "DR",
    "BOULEVARD": "BLVD",
    "SUITE": "STE",
    "NORTH": "N",
    "SOUTH": "S",
    "EAST": "E",
    "WEST": "W",
    "NORTHEAST": "NE",
    "NORTHWEST": "NW",
    "SOUTHEAST": "SE",
    "SOUTHWEST": "SW",
    "LANE": "LN",
    "COURT": "CT",
    "PLACE": "PL",
    "PLAZA": "PLZ",
    "SQUARE": "SQ",
    "HIGHWAY": "HWY",
    "PARKWAY": "PKWY",
    "EXPRESSWAY": "EXPY",
    "TERRACE": "TER",
    "CIRCLE": "CIR",
    "TRAIL": "TRL",
    "APARTMENT": "APT",
    "BUILDING": "BLDG",
    "FLOOR": "FL",
}

_ENTITY_FIELDS = (
    "record_id", "source_id", "name", "address", "city",
    "state", "zip", "phone", "lat", "lon",
)


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def _clean_text(value: object) -> str:
    """Uppercase, drop apostrophes/periods, space out other punctuation,
    collapse whitespace."""
    text = "" if value is None else str(value)
    text = text.upper()
    text = re.sub(r"['.]", "", text)
    text = re.sub(r"[^A-Z0-9 ]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_name(value: object) -> str:
    tokens = [_NAME_TOKEN_MAP.get(tok, tok) for tok in _clean_text(value).split()]
    while len(tokens) > 1 and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def _normalize_address(value: object) -> str:
    tokens = [_ADDRESS_TOKEN_MAP.get(tok, tok) for tok in _clean_text(value).split()]
    return " ".join(tokens)


def _normalize_phone(value: object) -> str:
    digits = re.sub(r"\D", "", "" if value is None else str(value))
    return digits[-10:]


def _normalize_zip5(value: object) -> str:
    digits = re.sub(r"\D", "", "" if value is None else str(value))
    return digits[:5]


def _to_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_record(rec: dict) -> dict:
    return {
        "record_id": str(rec.get("record_id", "")),
        "source_id": str(rec.get("source_id", "") or ""),
        "name": _normalize_name(rec.get("name")),
        "address": _normalize_address(rec.get("address")),
        "city": _clean_text(rec.get("city")),
        "state": _clean_text(rec.get("state")),
        "zip": _normalize_zip5(rec.get("zip")),
        "phone": _normalize_phone(rec.get("phone")),
        "lat": _to_float(rec.get("lat")),
        "lon": _to_float(rec.get("lon")),
    }


# ---------------------------------------------------------------------------
# Similarity
# ---------------------------------------------------------------------------

def _token_set_jaccard(a: str, b: str) -> float:
    ta, tb = set(a.split()), set(b.split())
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _jaro(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if not len1 or not len2:
        return 0.0
    window = max(max(len1, len2) // 2 - 1, 0)
    m1 = [False] * len1
    m2 = [False] * len2
    matches = 0
    for i, ch in enumerate(s1):
        start = max(0, i - window)
        end = min(i + window + 1, len2)
        for j in range(start, end):
            if m2[j] or s2[j] != ch:
                continue
            m1[i] = True
            m2[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    k = 0
    transpositions = 0
    for i in range(len1):
        if not m1[i]:
            continue
        while not m2[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    transpositions //= 2
    return (
        matches / len1
        + matches / len2
        + (matches - transpositions) / matches
    ) / 3.0


def _jaro_winkler(s1: str, s2: str, prefix_scale: float = 0.1) -> float:
    jaro = _jaro(s1, s2)
    prefix = 0
    for a, b in zip(s1, s2):
        if a != b or prefix >= 4:
            break
        prefix += 1
    return jaro + prefix * prefix_scale * (1.0 - jaro)


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    )
    return 2.0 * radius_m * math.asin(math.sqrt(min(1.0, a)))


# ---------------------------------------------------------------------------
# Union-find
# ---------------------------------------------------------------------------

class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def _compare(
    a: dict, b: dict, threshold: float, max_distance_m: float, require_same_zip5: bool
) -> tuple[float, float | None, bool]:
    score = max(
        _token_set_jaccard(a["name"], b["name"]),
        _jaro_winkler(a["name"], b["name"]),
    )
    distance_m: float | None = None
    if None not in (a["lat"], a["lon"], b["lat"], b["lon"]):
        distance_m = _haversine_m(a["lat"], a["lon"], b["lat"], b["lon"])
    matched = score >= threshold
    if matched and distance_m is not None and distance_m > max_distance_m:
        matched = False
    if matched and require_same_zip5 and (not a["zip"] or a["zip"] != b["zip"]):
        matched = False
    return score, distance_m, matched


def _block_keys(rec: dict) -> list[tuple]:
    """Union-of-keys blocking for one normalized record.

    A record joins its zip block when a zip5 exists, AND geographic grid
    blocks (its ~1.1 km cell plus the 8 neighbors) when coordinates exist.
    Records missing postal codes - common in OSM-derived data - would
    silently escape zip-only blocking and never be compared against
    official records of the same facility; the geo keys close that gap.
    Records with neither zip nor coordinates fall back to a name-initial
    block so they are still comparable.
    """
    first = rec["name"][:1]
    keys: list[tuple] = []
    if rec["zip"]:
        keys.append(("zip", rec["zip"], first))
    if rec["lat"] is not None and rec["lon"] is not None:
        cell_lat = int(math.floor(rec["lat"] * 100.0))
        cell_lon = int(math.floor(rec["lon"] * 100.0))
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                keys.append(("geo", cell_lat + dy, cell_lon + dx, first))
    if not keys:
        keys.append(("name", first))
    return keys


def _dedupe(records: list[dict], policy: dict) -> dict:
    """Run the full normalize/block/score/cluster pipeline.

    Returns entities, match decisions, and pairing stats. Pure helper so
    the idempotency proof can re-run it on canonical entities.
    """
    threshold = float(policy.get("name_similarity_threshold", 0.85))
    max_distance_m = float(policy.get("max_distance_m", 250.0))
    require_same_zip5 = bool(policy.get("require_same_zip5", True))

    normalized = [_normalize_record(rec) for rec in records]
    n = len(normalized)

    blocks: dict[tuple, list[int]] = {}
    for idx, rec in enumerate(normalized):
        for key in _block_keys(rec):
            blocks.setdefault(key, []).append(idx)

    candidate_pairs: set[tuple[int, int]] = set()
    for key in sorted(blocks):
        members = blocks[key]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a_idx, b_idx = members[i], members[j]
                candidate_pairs.add((min(a_idx, b_idx), max(a_idx, b_idx)))

    uf = _UnionFind(n)
    decisions: list[dict] = []
    pairs_compared = 0
    for a_idx, b_idx in sorted(candidate_pairs):
        pairs_compared += 1
        score, distance_m, matched = _compare(
            normalized[a_idx], normalized[b_idx],
            threshold, max_distance_m, require_same_zip5,
        )
        if matched:
            uf.union(a_idx, b_idx)
        if len(decisions) < MATCH_DECISION_CAP:
            decisions.append({
                "a": normalized[a_idx]["record_id"],
                "b": normalized[b_idx]["record_id"],
                "score": round(score, 4),
                "distance_m": (
                    round(distance_m, 1) if distance_m is not None else None
                ),
                "matched": matched,
            })

    clusters: dict[int, list[int]] = {}
    for idx in range(n):
        clusters.setdefault(uf.find(idx), []).append(idx)

    entities = [
        _canonical_entity([normalized[i] for i in member_idxs])
        for _, member_idxs in sorted(clusters.items())
    ]
    entities.sort(key=lambda e: e["entity_id"])

    pairs_possible = n * (n - 1) // 2
    return {
        "entities": entities,
        "match_decisions": decisions,
        "stats": {
            "input_records": n,
            "entities": len(entities),
            "duplicates_merged": n - len(entities),
            "pairs_compared": pairs_compared,
            "pairs_possible": pairs_possible,
            "blocking_reduction_ratio": (
                round(pairs_compared / pairs_possible, 6) if pairs_possible else 0.0
            ),
        },
    }


def _canonical_entity(members: list[dict]) -> dict:
    """Fold a cluster of normalized records into one canonical entity."""
    member_ids = sorted(m["record_id"] for m in members)
    entity_id = "ent:" + hashlib.sha256(
        "|".join(member_ids).encode("utf-8")
    ).hexdigest()[:12]

    # Longest normalized name; ties broken lexicographically for determinism.
    name = sorted((m["name"] for m in members), key=lambda s: (-len(s), s))[0]

    def first_nonempty(field: str) -> object:
        for m in members:
            value = m[field]
            if value not in (None, ""):
                return value
        return None if field in ("lat", "lon") else ""

    return {
        "entity_id": entity_id,
        "name": name,
        "address": first_nonempty("address"),
        "city": first_nonempty("city"),
        "state": first_nonempty("state"),
        "zip": first_nonempty("zip"),
        "phone": first_nonempty("phone"),
        "lat": first_nonempty("lat"),
        "lon": first_nonempty("lon"),
        "source_ids": sorted({m["source_id"] for m in members if m["source_id"]}),
        "member_record_ids": member_ids,
    }


def _validate_payload(payload: dict) -> tuple[bool, str]:
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        return False, "records must be a nonempty list"
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            return False, f"records[{idx}] is not an object"
        if not str(rec.get("record_id", "")):
            return False, f"records[{idx}] missing record_id"
    policy = payload.get("match_policy")
    if not isinstance(policy, dict):
        return False, "match_policy must be an object"
    threshold = policy.get("name_similarity_threshold", 0.85)
    if not isinstance(threshold, (int, float)) or not 0.0 <= float(threshold) <= 1.0:
        return False, "name_similarity_threshold must be a float in [0, 1]"
    max_dist = policy.get("max_distance_m", 250.0)
    if not isinstance(max_dist, (int, float)) or float(max_dist) < 0.0:
        return False, "max_distance_m must be a non-negative number"
    record_ids = [str(rec.get("record_id")) for rec in records]
    if len(set(record_ids)) != len(record_ids):
        return False, "record_id values must be unique"
    return True, f"{len(records)} records and match_policy validated"


def entity_normalize_and_dedupe(payload: dict) -> PrimitiveOutcome:
    """Normalize place records and cluster duplicates into entities.

    payload:
        records: nonempty list of place records with record_id,
            source_id, name, address, city, state, zip, phone, lat, lon
        match_policy: {name_similarity_threshold: float in [0, 1],
            max_distance_m: float, require_same_zip5: bool}

    Behavior: normalizes names (uppercase, punctuation stripped, common
    suffix rewrites, legal suffixes dropped), addresses (USPS-style
    abbreviations), phones (last 10 digits), zips (zip5). Blocks pairs
    by (zip5, first name char); scores blocked pairs with
    max(token-set Jaccard, Jaro-Winkler); enforces haversine distance
    and zip constraints; clusters matches with union-find.

    proofs:
        schema_validation - payload shape and policy ranges
        no_cross_state_merge - no entity spans two distinct states
        idempotency_test - re-running dedupe over the canonical
            entities produces no further merges
    """
    schema_ok, schema_detail = _validate_payload(payload)
    proofs = [ProofResult("schema_validation", schema_ok, schema_detail)]
    if not schema_ok:
        return PrimitiveOutcome(
            output={
                "entities": [],
                "match_decisions": [],
                "stats": {
                    "input_records": 0,
                    "entities": 0,
                    "duplicates_merged": 0,
                    "pairs_compared": 0,
                    "pairs_possible": 0,
                    "blocking_reduction_ratio": 0.0,
                },
            },
            effects_observed=["none"],
            proof_results=proofs,
        )

    records = payload["records"]
    policy = payload["match_policy"]
    result = _dedupe(records, policy)

    # Proof: no entity mixes two distinct non-empty states.
    normalized_by_id = {
        norm["record_id"]: norm for norm in (_normalize_record(r) for r in records)
    }
    cross_state = []
    for entity in result["entities"]:
        states = {
            normalized_by_id[rid]["state"]
            for rid in entity["member_record_ids"]
            if normalized_by_id[rid]["state"]
        }
        if len(states) > 1:
            cross_state.append(f"{entity['entity_id']}:{sorted(states)}")
    proofs.append(
        ProofResult(
            "no_cross_state_merge",
            not cross_state,
            "no entity spans multiple states"
            if not cross_state
            else "cross-state entities: " + "; ".join(cross_state),
        )
    )

    # Proof: dedupe over the canonical entities is a fixed point.
    entity_records = [
        {
            "record_id": e["entity_id"],
            "source_id": e["source_ids"][0] if e["source_ids"] else "",
            "name": e["name"],
            "address": e["address"],
            "city": e["city"],
            "state": e["state"],
            "zip": e["zip"],
            "phone": e["phone"],
            "lat": e["lat"],
            "lon": e["lon"],
        }
        for e in result["entities"]
    ]
    if entity_records:
        rerun = _dedupe(entity_records, policy)
        idempotent = rerun["stats"]["entities"] == len(entity_records)
        idem_detail = (
            f"re-run kept {len(entity_records)} entities"
            if idempotent
            else (
                f"re-run merged {len(entity_records)} entities down to "
                f"{rerun['stats']['entities']}"
            )
        )
    else:
        idempotent, idem_detail = True, "no entities to re-run"
    proofs.append(ProofResult("idempotency_test", idempotent, idem_detail))

    return PrimitiveOutcome(
        output=result,
        effects_observed=["none"],
        proof_results=proofs,
    )
