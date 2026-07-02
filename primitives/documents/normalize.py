"""Deterministic value normalization for the document-extraction lane.

Exposes:

- :func:`normalize_value` -- a pure helper ``(raw, normalization, value_type)
  -> (normalized_value, receipt)`` shared by the extraction primitives.
- :func:`value_normalize` -- the ``prim:document_extraction.value_normalize``
  primitive, a :class:`PrimitiveOutcome`-returning wrapper with proofs.
- shape helpers :func:`raw_value_type_ok` / :func:`looks_like_date` used by the
  locate/verify primitives for value-type validation.

HONESTY: normalization discards surface form. Every transform that changes the
raw string is flagged ``lossy=True`` with a reason so the original wording is
never silently lost. Each transform is idempotent -- normalizing an already
normalized value yields the same value -- and a proof asserts this.

Stdlib only. Pure computation: effects_observed == ["none"].
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

from primitives.core import PrimitiveOutcome, ProofResult

KNOWN_NORMALIZATIONS = (
    "iso_date",
    "currency_decimal",
    "percentage_fraction",
    "duration_iso8601",
    "number_parse",
    "boolean_normalize",
    "party_canonical",
    "none",
)

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}

_ENTITY_SUFFIXES = {
    "INC", "LLC", "LP", "LLP", "CORP", "CORPORATION", "CO", "LTD",
    "PLLC", "PC", "LC", "NA",
}

_TRUE_TOKENS = {
    "true", "yes", "y", "1", "affirmative", "shall", "x", "checked", "agreed",
}
_FALSE_TOKENS = {
    "false", "no", "n", "0", "negative", "not applicable", "n/a", "none",
}

_ISO_DURATION = re.compile(
    r"^P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?(?:T(?:\d+H)?(?:\d+M)?(?:\d+S)?)?$"
)

# Format a normalized value is expected to have, keyed by normalization.
_TARGET_PATTERNS = {
    "iso_date": r"^\d{4}-\d{2}-\d{2}$",
    "currency_decimal": r"^-?\d+\.\d{2}$",
    "percentage_fraction": r"^-?\d+(?:\.\d+)?$",
    "duration_iso8601": r"^P(?:\d+Y)?(?:\d+M)?(?:\d+W)?(?:\d+D)?"
                        r"(?:T(?:\d+H)?(?:\d+M)?(?:\d+S)?)?$",
    "number_parse": r"^-?\d+(?:\.\d+)?$",
    "boolean_normalize": r"^(?:true|false)$",
    "party_canonical": r"^[A-Z0-9 ]+$",
    "none": r".*",
}

# Which value_types a normalization is meaningfully coherent with.
_COHERENT_TYPES = {
    "iso_date": {"date", "date_range", "datetime"},
    "currency_decimal": {"money_amount", "currency", "number"},
    "percentage_fraction": {"percentage", "fraction", "number"},
    "duration_iso8601": {"duration"},
    "number_parse": {"number", "integer", "quantity_with_unit"},
    "boolean_normalize": {"boolean"},
    "party_canonical": {"party_entity", "person_name", "org_name"},
    "none": set(),  # none is coherent with any type
}


# ---------------------------------------------------------------------------
# Shape helpers (used by locate + verify for value_type_validation)
# ---------------------------------------------------------------------------

def looks_like_date(value: str) -> bool:
    if not re.search(r"\d", value):
        return False
    if re.search(r"[/-]", value):
        return True
    return bool(re.search(
        r"(?i)(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", value
    ))


def raw_value_type_ok(value: str, value_type: str) -> bool:
    """Loose shape check on a RAW extracted value against its value_type."""
    if not isinstance(value, str):
        return False
    v = value.strip()
    if not v:
        return False
    if value_type in ("date", "date_range", "datetime"):
        return looks_like_date(v)
    if value_type in ("money_amount", "currency"):
        return bool(re.search(r"\d", v))
    if value_type == "percentage":
        return "%" in v or bool(re.search(r"\d", v))
    if value_type in ("number", "integer", "quantity_with_unit"):
        return bool(re.search(r"\d", v))
    if value_type == "duration":
        return bool(re.search(r"\d", v))
    if value_type == "boolean":
        return v.lower() in (_TRUE_TOKENS | _FALSE_TOKENS)
    if value_type in ("party_entity", "person_name", "org_name",
                      "free_text_clause"):
        return bool(re.search(r"[A-Za-z]", v))
    if value_type in ("identifier", "enum_category", "address"):
        return bool(re.search(r"[A-Za-z0-9]", v))
    # Unknown value_type: accept any non-empty value.
    return True


# ---------------------------------------------------------------------------
# Per-normalization transforms (pure)
# ---------------------------------------------------------------------------

def _dec_str(d: Decimal) -> str:
    """Fixed-point string for a Decimal with no scientific notation and no
    trailing zeros (but at least one digit)."""
    d = d.normalize()
    s = format(d, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s if s else "0"


def _norm_iso_date(raw: str) -> tuple[str, dict]:
    s = raw.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
        if m:
            mo, d, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        else:
            m = re.search(
                r"(?i)\b([A-Za-z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b",
                s,
            )
            if m and m.group(1).lower() in _MONTHS:
                mo = _MONTHS[m.group(1).lower()]
                d = int(m.group(2))
                y = int(m.group(3))
            else:
                m = re.search(
                    r"(?i)(\d{1,2})(?:st|nd|rd|th)?\s+day\s+of\s+"
                    r"([A-Za-z]+),?\s+(\d{4})",
                    s,
                )
                if not m or m.group(2).lower() not in _MONTHS:
                    raise ValueError(f"iso_date: unrecognized date {raw!r}")
                d = int(m.group(1))
                mo = _MONTHS[m.group(2).lower()]
                y = int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        raise ValueError(f"iso_date: out-of-range date {raw!r}")
    normalized = f"{y:04d}-{mo:02d}-{d:02d}"
    return normalized, {"reason": "surface date format discarded; "
                        "normalized to ISO 8601 calendar date"}


def _norm_currency_decimal(raw: str) -> tuple[str, dict]:
    cleaned = re.sub(r"[^\d.\-]", "", raw)
    if not re.search(r"\d", cleaned):
        raise ValueError(f"currency_decimal: no digits in {raw!r}")
    try:
        amount = Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"currency_decimal: cannot parse {raw!r}: {exc}")
    detected = "$" if "$" in raw else ("USD" if "usd" in raw.lower() else "")
    return str(amount), {
        "currency": "USD",
        "detected_symbol": detected,
        "reason": "currency symbol and grouping separators discarded; "
                  "amount is USD (recorded in receipt.currency)",
    }


def _norm_percentage_fraction(raw: str) -> tuple[str, dict]:
    s = raw.strip()
    cleaned = re.sub(r"[^\d.\-]", "", s)
    if not re.search(r"\d", cleaned):
        raise ValueError(f"percentage_fraction: no digits in {raw!r}")
    num = Decimal(cleaned)
    if s.endswith("%"):
        frac = num / Decimal(100)
        return _dec_str(frac), {
            "reason": "percent surface form discarded; expressed as fraction "
                      "of one",
        }
    # No percent sign: treat the value as an already-normalized fraction.
    return _dec_str(num), {"reason": ""}


def _norm_duration(raw: str) -> tuple[str, dict]:
    s = raw.strip().upper()
    if s != "P" and _ISO_DURATION.fullmatch(s):
        return s, {"reason": ""}
    low = raw.lower()
    mnum = re.search(r"\((\d+)\)", raw) or re.search(r"(\d+)", raw)
    if not mnum:
        raise ValueError(f"duration_iso8601: no count in {raw!r}")
    n = mnum.group(1)
    if "year" in low:
        normalized = f"P{n}Y"
    elif "month" in low:
        normalized = f"P{n}M"
    elif "week" in low:
        normalized = f"P{n}W"
    elif "day" in low:
        normalized = f"P{n}D"
    elif "hour" in low:
        normalized = f"PT{n}H"
    elif "minute" in low:
        normalized = f"PT{n}M"
    elif "second" in low:
        normalized = f"PT{n}S"
    else:
        raise ValueError(f"duration_iso8601: no time unit in {raw!r}")
    return normalized, {"reason": "natural-language duration discarded; "
                        "expressed as ISO 8601 duration"}


def _norm_number(raw: str) -> tuple[str, dict]:
    m = re.search(r"-?\d[\d,]*(?:\.\d+)?", raw)
    if not m:
        raise ValueError(f"number_parse: no number in {raw!r}")
    normalized = m.group(0).replace(",", "")
    return normalized, {"reason": "grouping separators and surrounding text "
                        "discarded"}


def _norm_boolean(raw: str) -> tuple[str, dict]:
    low = raw.strip().lower()
    if low in _TRUE_TOKENS:
        return "true", {"reason": "surface token mapped to canonical boolean"}
    if low in _FALSE_TOKENS:
        return "false", {"reason": "surface token mapped to canonical boolean"}
    raise ValueError(f"boolean_normalize: unrecognized boolean {raw!r}")


def _norm_party_canonical(raw: str) -> tuple[str, dict]:
    up = raw.upper()
    cleaned = re.sub(r"[^\w\s]", " ", up)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        raise ValueError(f"party_canonical: empty after cleaning {raw!r}")
    tokens = cleaned.split()
    suffix = ""
    if len(tokens) > 1 and tokens[-1] in _ENTITY_SUFFIXES:
        suffix = tokens[-1]
        tokens = tokens[:-1]
    normalized = " ".join(tokens)
    return normalized, {
        "suffix": suffix,
        "reason": "uppercased, punctuation stripped"
                  + (f", entity suffix {suffix!r} moved to receipt.suffix"
                     if suffix else ""),
    }


_TRANSFORMS = {
    "iso_date": _norm_iso_date,
    "currency_decimal": _norm_currency_decimal,
    "percentage_fraction": _norm_percentage_fraction,
    "duration_iso8601": _norm_duration,
    "number_parse": _norm_number,
    "boolean_normalize": _norm_boolean,
    "party_canonical": _norm_party_canonical,
}


# ---------------------------------------------------------------------------
# Shared pure helper
# ---------------------------------------------------------------------------

def normalize_value(
    raw_value: str, normalization: str, value_type: str = "none"
) -> tuple[str, dict]:
    """Normalize ``raw_value`` and return ``(normalized_value, receipt)``.

    ``receipt`` always carries ``normalization``, ``lossy`` (bool), and
    ``reason``. Unknown/unsupported normalizations pass the value through
    unchanged and record ``note='passthrough_unsupported'`` rather than
    raising, so callers with a broader normalization vocabulary never crash.
    """
    if not isinstance(raw_value, str):
        raise ValueError("raw_value must be a string")
    if normalization == "none":
        return raw_value, {
            "normalization": "none", "lossy": False, "reason": "",
        }
    fn = _TRANSFORMS.get(normalization)
    if fn is None:
        return raw_value, {
            "normalization": normalization, "lossy": False, "reason": "",
            "note": "passthrough_unsupported",
        }
    normalized, extra = fn(raw_value)
    lossy = normalized.strip() != raw_value.strip()
    receipt = {"normalization": normalization, "lossy": lossy}
    receipt.update(extra)
    if not lossy:
        receipt["reason"] = ""
    return normalized, receipt


# ---------------------------------------------------------------------------
# Coherence check on a NORMALIZED value (proof helper)
# ---------------------------------------------------------------------------

def _value_type_coherent(
    normalized: str, normalization: str, value_type: str
) -> bool:
    pattern = _TARGET_PATTERNS.get(normalization, r".*")
    if not re.fullmatch(pattern, normalized):
        return False
    allowed = _COHERENT_TYPES.get(normalization, set())
    if not allowed:  # none / unknown -> coherent with any type
        return True
    if value_type in allowed:
        return True
    # An unrecognized value_type is not treated as an incoherence; the format
    # match above is the load-bearing guarantee.
    known = set().union(*_COHERENT_TYPES.values())
    return value_type not in known


# ---------------------------------------------------------------------------
# Primitive: value_normalize
# ---------------------------------------------------------------------------

def value_normalize(payload: dict) -> PrimitiveOutcome:
    """prim:document_extraction.value_normalize.

    payload: {"raw_value": str, "normalization": str, "value_type": str}
    output:  {"raw_value","normalized_value","normalization","lossy","receipt"}
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    raw_value = payload.get("raw_value")
    normalization = payload.get("normalization")
    value_type = payload.get("value_type", "none")
    errors: list[str] = []
    if not isinstance(raw_value, str) or not raw_value.strip():
        errors.append("'raw_value' must be a non-empty string")
    if normalization not in KNOWN_NORMALIZATIONS:
        errors.append(
            "'normalization' must be one of " + ", ".join(KNOWN_NORMALIZATIONS)
        )
    if not isinstance(value_type, str) or not value_type:
        errors.append("'value_type' must be a non-empty string")
    if errors:
        raise ValueError("schema_validation failed: " + "; ".join(errors))

    normalized, receipt = normalize_value(raw_value, normalization, value_type)
    lossy = bool(receipt.get("lossy", False))

    # normalization_roundtrip: the transform must be idempotent, and any lossy
    # transform must disclose a reason. Idempotency is the reversibility
    # guarantee we can actually check; lossiness is disclosed honestly.
    renorm, _ = normalize_value(normalized, normalization, value_type)
    idempotent = renorm == normalized
    reason_ok = (not lossy) or bool(receipt.get("reason"))
    roundtrip_detail = (
        f"idempotent={idempotent}; lossy={lossy}; "
        f"reason={receipt.get('reason', '')!r}"
    )

    coherent = _value_type_coherent(normalized, normalization, value_type)

    output = {
        "raw_value": raw_value,
        "normalized_value": normalized,
        "normalization": normalization,
        "lossy": lossy,
        "receipt": receipt,
    }
    proofs = [
        ProofResult("schema_validation", True,
                    f"normalization={normalization}, value_type={value_type}"),
        ProofResult("normalization_roundtrip", idempotent and reason_ok,
                    roundtrip_detail),
        ProofResult("value_type_coherent", coherent,
                    f"normalized={normalized!r} coherent with "
                    f"value_type={value_type!r}: {coherent}"),
    ]
    return PrimitiveOutcome(
        output=output,
        effects_observed=["none"],
        proof_results=proofs,
    )
