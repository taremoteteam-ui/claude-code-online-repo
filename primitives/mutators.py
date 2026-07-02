"""Deterministic remix mutators for the place-discovery-geospatial lane.

The "adapt a near-match instead of regenerating" layer: each mutator is a
pure, deterministic format/route transformation that reshapes an
almost-right payload into the needed shape while disclosing exactly what
the transformation preserves or drops.

Every mutator:

- is ``def <name>(payload: dict) -> PrimitiveOutcome``;
- includes a ``mutation_receipt`` dict in its output::

      {"mutator": ..., "lossiness": "lossless"|"lossy",
       "fields_dropped": [...], "preconditions_checked": [...]}

- reports ``effects_observed == ["none"]`` (pure computation, no I/O);
- runs its own proofs, including a roundtrip test wherever losslessness
  is claimed. The one lossy mutator (:func:`field_project`) discloses
  every dropped field instead of claiming a roundtrip.

HONESTY NOTES
- "Lossless" tabular mutators over heterogeneous records preserve cell
  content modulo one disclosed normalization: a missing key and an
  explicit null become the same null cell. Each such mutator lists the
  normalization in ``preconditions_checked`` and its roundtrip proof
  compares against the normalized originals.
- GeoJSON positions are [lon, lat] order per RFC 7946; record fields are
  named ``lat``/``lon`` keys. :func:`geojson_points_to_records` emits an
  explicit ``coordinate_order`` receipt and a proof spot-checks the
  mapping on every feature so the axes cannot silently swap.

Stdlib only. Outputs are candidate material; nothing here promotes truth.
"""

from __future__ import annotations

import json

from primitives.core import PrimitiveOutcome, ProofResult, canonical_hash


# ---------------------------------------------------------------------------
# Shared helpers (pure functions, stdlib only)
# ---------------------------------------------------------------------------

def _ckey(value: object) -> str:
    """Deterministic canonical JSON string usable as a set/dict key."""
    return json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _mutation_receipt(
    mutator: str,
    lossiness: str,
    fields_dropped: list,
    preconditions_checked: list,
) -> dict:
    return {
        "mutator": mutator,
        "lossiness": lossiness,
        "fields_dropped": list(fields_dropped),
        "preconditions_checked": list(preconditions_checked),
    }


def _validate_records(records: object, errors: list, label: str = "records") -> bool:
    """True when ``records`` is a (possibly empty) list of string-keyed dicts."""
    if not isinstance(records, list):
        errors.append(f"'{label}' must be a list")
        return False
    ok = True
    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append(f"{label}[{idx}] is not an object")
            ok = False
            continue
        for key in rec:
            if not isinstance(key, str):
                errors.append(f"{label}[{idx}] has a non-string key {key!r}")
                ok = False
    return ok


def _validate_string_list(
    value: object, errors: list, label: str, allow_empty: bool = False
) -> bool:
    """True when ``value`` is a list of unique nonempty strings."""
    if not isinstance(value, list):
        errors.append(f"'{label}' must be a list of strings")
        return False
    if not value and not allow_empty:
        errors.append(f"'{label}' must be a non-empty list")
        return False
    ok = True
    seen: set[str] = set()
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item:
            errors.append(f"{label}[{idx}] must be a nonempty string")
            ok = False
            continue
        if item in seen:
            errors.append(f"'{label}' contains duplicate {item!r}")
            ok = False
        seen.add(item)
    return ok


def _records_to_rows(records: list, columns: list) -> list:
    return [[rec.get(col) for col in columns] for rec in records]


def _rows_to_records(columns: list, rows: list) -> list:
    return [dict(zip(columns, row)) for row in rows]


def _apply_rename(records: list, rename_map: dict) -> list:
    return [{rename_map.get(k, k): v for k, v in rec.items()} for rec in records]


def _widen(
    long_records: list, id_fields: list, var_field: str, value_field: str
) -> tuple[list, list, list]:
    """Group long rows into wide records.

    Returns ``(wide_records, var_order, conflicts)`` where ``conflicts``
    lists every (id, var) cell that appears twice with DIFFERENT values.
    An identical duplicate row collapses silently into the same cell.
    """
    groups: dict[str, dict] = {}
    group_order: list[str] = []
    var_order: list[str] = []
    cells: dict[tuple[str, str], object] = {}
    conflicts: list[str] = []
    for rec in long_records:
        id_part = {f: rec[f] for f in id_fields}
        gkey = _ckey(id_part)
        if gkey not in groups:
            groups[gkey] = dict(id_part)
            group_order.append(gkey)
        var = rec[var_field]
        value = rec[value_field]
        if var not in var_order:
            var_order.append(var)
        cell = (gkey, var)
        if cell in cells:
            if _ckey(cells[cell]) != _ckey(value):
                conflicts.append(
                    f"id={gkey} var={var!r}: {cells[cell]!r} != {value!r}"
                )
            continue
        cells[cell] = value
        groups[gkey][var] = value
    return [groups[g] for g in group_order], var_order, conflicts


def _lengthen_present(
    wide_records: list,
    id_fields: list,
    var_order: list,
    var_field: str,
    value_field: str,
) -> list:
    """Re-melt wide records, emitting one long row per PRESENT var key."""
    rows = []
    for rec in wide_records:
        id_part = {f: rec[f] for f in id_fields}
        for var in var_order:
            if var in rec:
                rows.append({**id_part, var_field: var, value_field: rec[var]})
    return rows


def _fc_from_records(records: list) -> dict:
    features = []
    for rec in records:
        props = {k: v for k, v in rec.items() if k not in ("lat", "lon")}
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [rec["lon"], rec["lat"]]},
            "properties": props,
        })
    return {"type": "FeatureCollection", "features": features}


def _records_from_fc(features: list) -> list:
    records = []
    for feat in features:
        coords = feat["geometry"]["coordinates"]
        records.append({**feat["properties"], "lat": coords[1], "lon": coords[0]})
    return records


# ---------------------------------------------------------------------------
# Mutator 1: json_records_to_rows
# ---------------------------------------------------------------------------

def json_records_to_rows(payload: dict) -> PrimitiveOutcome:
    """Pivot a list of JSON records into a columns + rows table.

    payload:
        records:      list of string-keyed objects
        column_order: optional explicit column list; must cover every key
                      observed in records (extra columns fill with null)

    output:
        columns, rows, mutation_receipt

    lossiness: lossless modulo the disclosed missing-key -> null
    normalization (a missing key and an explicit null become the same
    null cell).

    proofs: schema_validation, column_coverage, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = [
        "records_are_string_keyed_objects",
        "column_order_covers_observed_keys",
        "missing_keys_normalized_to_null",
    ]
    receipt = _mutation_receipt("json_records_to_rows", "lossless", [], preconditions)

    errors: list[str] = []
    records = payload.get("records")
    column_order = payload.get("column_order")
    records_ok = _validate_records(records, errors)
    if column_order is not None:
        _validate_string_list(column_order, errors, "column_order", allow_empty=True)
    proofs = [
        ProofResult(
            "schema_validation",
            not errors,
            "; ".join(errors) if errors else f"{len(records or [])} records validated",
        )
    ]
    if errors or not records_ok:
        return PrimitiveOutcome(
            output={"columns": [], "rows": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    observed: set[str] = set()
    for rec in records:
        observed.update(rec.keys())
    if column_order is not None:
        columns = list(column_order)
        missing = sorted(observed - set(columns))
    else:
        columns = sorted(observed)
        missing = []
    proofs.append(
        ProofResult(
            "column_coverage",
            not missing,
            (f"{len(columns)} columns cover all {len(observed)} observed keys"
             if not missing
             else "column_order omits observed keys: " + ", ".join(missing)),
        )
    )
    if missing:
        return PrimitiveOutcome(
            output={"columns": [], "rows": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    rows = _records_to_rows(records, columns)
    rebuilt = _rows_to_records(columns, rows)
    normalized = [{col: rec.get(col) for col in columns} for rec in records]
    roundtrip_ok = canonical_hash(rebuilt) == canonical_hash(normalized)
    proofs.append(
        ProofResult(
            "roundtrip_test",
            roundtrip_ok,
            (f"{len(records)} records reproduced via rows_to_json_records inverse "
             "modulo key order; missing keys normalized to null"
             if roundtrip_ok
             else "inverse reconstruction diverged from normalized input records"),
        )
    )
    return PrimitiveOutcome(
        output={"columns": columns, "rows": rows, "mutation_receipt": receipt},
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Mutator 2: rows_to_json_records
# ---------------------------------------------------------------------------

def rows_to_json_records(payload: dict) -> PrimitiveOutcome:
    """Rebuild JSON records from a columns + rows table.

    payload:
        columns: list of unique column-name strings
        rows:    list of row arrays, each exactly len(columns) long

    output:
        records, mutation_receipt

    lossiness: lossless (exact inverse of json_records_to_rows).

    proofs: schema_validation, width_consistency, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = [
        "columns_are_unique_strings",
        "row_width_matches_columns",
    ]
    receipt = _mutation_receipt("rows_to_json_records", "lossless", [], preconditions)

    errors: list[str] = []
    columns = payload.get("columns")
    rows = payload.get("rows")
    columns_ok = _validate_string_list(columns, errors, "columns", allow_empty=True)
    if not isinstance(rows, list):
        errors.append("'rows' must be a list")
    else:
        for idx, row in enumerate(rows):
            if not isinstance(row, list):
                errors.append(f"rows[{idx}] is not an array")
    proofs = [
        ProofResult(
            "schema_validation",
            not errors,
            "; ".join(errors) if errors
            else f"{len(columns)} columns, {len(rows)} rows validated",
        )
    ]
    if errors or not columns_ok:
        return PrimitiveOutcome(
            output={"records": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    bad_widths = [
        f"rows[{idx}] has {len(row)} cells, expected {len(columns)}"
        for idx, row in enumerate(rows)
        if len(row) != len(columns)
    ]
    proofs.append(
        ProofResult(
            "width_consistency",
            not bad_widths,
            (f"all {len(rows)} rows are {len(columns)} cells wide"
             if not bad_widths else "; ".join(bad_widths)),
        )
    )
    if bad_widths:
        return PrimitiveOutcome(
            output={"records": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    records = _rows_to_records(columns, rows)
    rebuilt_rows = _records_to_rows(records, columns)
    roundtrip_ok = canonical_hash(rebuilt_rows) == canonical_hash(rows)
    proofs.append(
        ProofResult(
            "roundtrip_test",
            roundtrip_ok,
            (f"{len(rows)} rows reproduced via json_records_to_rows inverse"
             if roundtrip_ok
             else "inverse reconstruction diverged from input rows"),
        )
    )
    return PrimitiveOutcome(
        output={"records": records, "mutation_receipt": receipt},
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Mutator 3: wide_to_long
# ---------------------------------------------------------------------------

def wide_to_long(payload: dict) -> PrimitiveOutcome:
    """Melt wide records into long (id, variable, value) records.

    payload:
        records:      list of wide record objects
        id_fields:    non-empty list of identifier field names; the id
                      tuple must be unique per record
        value_fields: non-empty list of measure field names to melt
        var_name:     long-format variable column name (default "variable")
        value_name:   long-format value column name (default "value")

    Every record key must belong to id_fields or value_fields (undeclared
    keys would be silently dropped, breaking the lossless claim, so they
    are a precondition violation). Missing value fields melt to null.

    output:
        records (long), mutation_receipt

    lossiness: lossless given id uniqueness, modulo the disclosed
    missing-key -> null normalization.

    proofs: schema_validation, row_count_arithmetic, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = [
        "id_fields_present_in_all_records",
        "id_tuples_unique",
        "id_and_value_fields_cover_all_keys",
        "missing_value_fields_normalized_to_null",
    ]
    receipt = _mutation_receipt("wide_to_long", "lossless", [], preconditions)

    errors: list[str] = []
    records = payload.get("records")
    id_fields = payload.get("id_fields")
    value_fields = payload.get("value_fields")
    var_name = payload.get("var_name", "variable")
    value_name = payload.get("value_name", "value")
    records_ok = _validate_records(records, errors)
    ids_ok = _validate_string_list(id_fields, errors, "id_fields")
    values_ok = _validate_string_list(value_fields, errors, "value_fields")
    if not isinstance(var_name, str) or not var_name:
        errors.append("'var_name' must be a nonempty string")
    if not isinstance(value_name, str) or not value_name:
        errors.append("'value_name' must be a nonempty string")
    if var_name == value_name:
        errors.append("'var_name' and 'value_name' must differ")
    if ids_ok and values_ok:
        overlap = sorted(set(id_fields) & set(value_fields))
        if overlap:
            errors.append(f"id_fields and value_fields overlap: {overlap}")
        for name in (var_name, value_name):
            if isinstance(name, str) and name in id_fields:
                errors.append(f"long column name {name!r} collides with an id field")
    if records_ok and ids_ok and values_ok and not errors:
        allowed = set(id_fields) | set(value_fields)
        seen_ids: set[str] = set()
        for idx, rec in enumerate(records):
            missing_ids = sorted(f for f in id_fields if f not in rec)
            if missing_ids:
                errors.append(f"records[{idx}] missing id fields {missing_ids}")
                continue
            extras = sorted(set(rec.keys()) - allowed)
            if extras:
                errors.append(
                    f"records[{idx}] has undeclared fields {extras} that would "
                    "be dropped"
                )
            gkey = _ckey({f: rec[f] for f in id_fields})
            if gkey in seen_ids:
                errors.append(f"records[{idx}] duplicate id tuple {gkey}")
            seen_ids.add(gkey)
    proofs = [
        ProofResult(
            "schema_validation",
            not errors,
            "; ".join(errors) if errors
            else (f"{len(records)} wide records validated; ids unique; "
                  "all keys declared"),
        )
    ]
    if errors:
        return PrimitiveOutcome(
            output={"records": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    long_records = []
    for rec in records:
        id_part = {f: rec[f] for f in id_fields}
        for vf in value_fields:
            long_records.append({**id_part, var_name: vf, value_name: rec.get(vf)})

    expected = len(records) * len(value_fields)
    proofs.append(
        ProofResult(
            "row_count_arithmetic",
            len(long_records) == expected,
            f"{len(long_records)} long rows == {len(records)} records * "
            f"{len(value_fields)} value fields",
        )
    )

    widened, _var_order, conflicts = _widen(
        long_records, id_fields, var_name, value_name
    )
    normalized = [
        {**{f: rec[f] for f in id_fields},
         **{vf: rec.get(vf) for vf in value_fields}}
        for rec in records
    ]
    roundtrip_ok = not conflicts and canonical_hash(widened) == canonical_hash(
        normalized
    )
    proofs.append(
        ProofResult(
            "roundtrip_test",
            roundtrip_ok,
            (f"{len(records)} wide records reproduced via long_to_wide inverse; "
             "missing value fields normalized to null"
             if roundtrip_ok
             else "inverse reconstruction diverged from normalized input records"),
        )
    )
    return PrimitiveOutcome(
        output={"records": long_records, "mutation_receipt": receipt},
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Mutator 4: long_to_wide
# ---------------------------------------------------------------------------

def long_to_wide(payload: dict) -> PrimitiveOutcome:
    """Pivot long (id, variable, value) records into wide records.

    payload:
        records:     list of long record objects whose keys are exactly
                     id_fields + var_field + value_field
        id_fields:   non-empty list of identifier field names
        var_field:   name of the variable-name column
        value_field: name of the value column

    The same (id, var) cell appearing twice with DIFFERENT values is a
    precondition violation (no_duplicate_cells fails with detail); an
    identical duplicate row collapses into the single cell it names.

    output:
        records (wide, id tuples in first-seen order), mutation_receipt

    lossiness: lossless over the set of distinct cells (identical
    duplicate long rows collapse to one cell; the roundtrip proof
    compares duplicate-collapsed sets).

    proofs: schema_validation, no_duplicate_cells, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = [
        "long_record_keys_exactly_ids_plus_var_plus_value",
        "var_values_are_strings",
        "var_values_do_not_collide_with_id_fields",
        "no_conflicting_duplicate_cells",
    ]
    receipt = _mutation_receipt("long_to_wide", "lossless", [], preconditions)

    errors: list[str] = []
    records = payload.get("records")
    id_fields = payload.get("id_fields")
    var_field = payload.get("var_field")
    value_field = payload.get("value_field")
    records_ok = _validate_records(records, errors)
    ids_ok = _validate_string_list(id_fields, errors, "id_fields")
    if not isinstance(var_field, str) or not var_field:
        errors.append("'var_field' must be a nonempty string")
    if not isinstance(value_field, str) or not value_field:
        errors.append("'value_field' must be a nonempty string")
    if var_field == value_field:
        errors.append("'var_field' and 'value_field' must differ")
    if ids_ok and not errors:
        for name in (var_field, value_field):
            if name in id_fields:
                errors.append(f"{name!r} collides with an id field")
    if records_ok and ids_ok and not errors:
        expected_keys = set(id_fields) | {var_field, value_field}
        for idx, rec in enumerate(records):
            if set(rec.keys()) != expected_keys:
                missing = sorted(expected_keys - set(rec.keys()))
                extras = sorted(set(rec.keys()) - expected_keys)
                errors.append(
                    f"records[{idx}] keys mismatch "
                    f"(missing={missing}, extra={extras})"
                )
                continue
            var = rec[var_field]
            if not isinstance(var, str) or not var:
                errors.append(
                    f"records[{idx}] {var_field!r} value must be a nonempty string"
                )
            elif var in id_fields:
                errors.append(
                    f"records[{idx}] var value {var!r} collides with an id field"
                )
    proofs = [
        ProofResult(
            "schema_validation",
            not errors,
            "; ".join(errors) if errors
            else f"{len(records)} long records validated",
        )
    ]
    if errors:
        return PrimitiveOutcome(
            output={"records": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    wide_records, var_order, conflicts = _widen(
        records, id_fields, var_field, value_field
    )
    proofs.append(
        ProofResult(
            "no_duplicate_cells",
            not conflicts,
            (f"{len(records)} long rows map to distinct (id, var) cells"
             if not conflicts
             else "conflicting duplicate cells: " + "; ".join(conflicts)),
        )
    )
    if conflicts:
        return PrimitiveOutcome(
            output={"records": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    reconstructed = _lengthen_present(
        wide_records, id_fields, var_order, var_field, value_field
    )
    original_set = {_ckey(rec) for rec in records}
    rebuilt_set = {_ckey(rec) for rec in reconstructed}
    roundtrip_ok = original_set == rebuilt_set
    proofs.append(
        ProofResult(
            "roundtrip_test",
            roundtrip_ok,
            (f"{len(rebuilt_set)} distinct cells reproduced via wide_to_long "
             "inverse (identical duplicate rows collapse to one cell)"
             if roundtrip_ok
             else "inverse reconstruction diverged from input long records"),
        )
    )
    return PrimitiveOutcome(
        output={"records": wide_records, "mutation_receipt": receipt},
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Mutator 5: field_rename
# ---------------------------------------------------------------------------

def field_rename(payload: dict) -> PrimitiveOutcome:
    """Rename record fields via an invertible old -> new map.

    payload:
        records:    list of record objects
        rename_map: {old_name: new_name}; values must be unique so the
                    inverse map is well defined

    Renaming onto an existing key is a precondition violation: either two
    keys of one record rename to the same name, or a record already holds
    a key that is some other key's rename target without being renamed
    itself (which would make the inverse map ambiguous).

    output:
        records (renamed, key order preserved), mutation_receipt

    lossiness: lossless (values untouched; the inverse map restores the
    original records exactly).

    proofs: schema_validation, no_collision, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = [
        "rename_map_is_invertible",
        "no_rename_collisions_in_any_record",
    ]
    receipt = _mutation_receipt("field_rename", "lossless", [], preconditions)

    errors: list[str] = []
    records = payload.get("records")
    rename_map = payload.get("rename_map")
    records_ok = _validate_records(records, errors)
    if not isinstance(rename_map, dict) or not rename_map:
        errors.append("'rename_map' must be a non-empty object")
        rename_map = {}
    else:
        for old, new in rename_map.items():
            if not isinstance(old, str) or not old:
                errors.append(f"rename_map key {old!r} must be a nonempty string")
            if not isinstance(new, str) or not new:
                errors.append(f"rename_map value {new!r} must be a nonempty string")
        values = list(rename_map.values())
        if len(set(values)) != len(values):
            dupes = sorted({v for v in values if values.count(v) > 1})
            errors.append(
                f"rename_map is not invertible: duplicate targets {dupes}"
            )
    proofs = [
        ProofResult(
            "schema_validation",
            not errors,
            "; ".join(errors) if errors
            else (f"{len(records)} records and {len(rename_map)} invertible "
                  "renames validated"),
        )
    ]
    if errors or not records_ok:
        return PrimitiveOutcome(
            output={"records": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    inverse = {new: old for old, new in rename_map.items()}
    collisions: list[str] = []
    for idx, rec in enumerate(records):
        new_keys = [rename_map.get(k, k) for k in rec]
        seen: set[str] = set()
        dupes: list[str] = []
        for nk in new_keys:
            if nk in seen and nk not in dupes:
                dupes.append(nk)
            seen.add(nk)
        for dup in dupes:
            collisions.append(f"records[{idx}]: rename collides on key {dup!r}")
        for key in rec:
            if key not in rename_map and key in inverse:
                collisions.append(
                    f"records[{idx}]: existing key {key!r} is the rename target "
                    f"of {inverse[key]!r} but is not itself renamed"
                )
    proofs.append(
        ProofResult(
            "no_collision",
            not collisions,
            (f"no rename collisions across {len(records)} records"
             if not collisions else "; ".join(collisions)),
        )
    )
    if collisions:
        return PrimitiveOutcome(
            output={"records": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    renamed = _apply_rename(records, rename_map)
    restored = _apply_rename(renamed, inverse)
    roundtrip_ok = canonical_hash(restored) == canonical_hash(records)
    proofs.append(
        ProofResult(
            "roundtrip_test",
            roundtrip_ok,
            (f"{len(records)} records restored exactly by the inverse rename map"
             if roundtrip_ok
             else "inverse rename diverged from input records"),
        )
    )
    return PrimitiveOutcome(
        output={"records": renamed, "mutation_receipt": receipt},
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Mutator 6: field_project (LOSSY)
# ---------------------------------------------------------------------------

def field_project(payload: dict) -> PrimitiveOutcome:
    """Project records onto a kept subset of fields. LOSSY.

    payload:
        records:     list of record objects
        keep_fields: non-empty list of field names to keep

    Every field outside keep_fields is dropped and disclosed in
    ``mutation_receipt.fields_dropped``. No roundtrip is claimed:
    lossiness is "lossy" by construction.

    output:
        records (projected, keep_fields order), mutation_receipt

    proofs: schema_validation, projection_exactness, drop_disclosure
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = [
        "keep_fields_are_unique_strings",
        "dropped_fields_fully_disclosed",
    ]

    errors: list[str] = []
    records = payload.get("records")
    keep_fields = payload.get("keep_fields")
    records_ok = _validate_records(records, errors)
    keep_ok = _validate_string_list(keep_fields, errors, "keep_fields")
    proofs = [
        ProofResult(
            "schema_validation",
            not errors,
            "; ".join(errors) if errors
            else f"{len(records)} records, {len(keep_fields)} keep fields validated",
        )
    ]
    if errors or not records_ok or not keep_ok:
        receipt = _mutation_receipt("field_project", "lossy", [], preconditions)
        return PrimitiveOutcome(
            output={"records": [], "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    keep_set = set(keep_fields)
    projected = [
        {field: rec[field] for field in keep_fields if field in rec}
        for rec in records
    ]
    fields_dropped = sorted(
        {key for rec in records for key in rec if key not in keep_set}
    )
    receipt = _mutation_receipt(
        "field_project", "lossy", fields_dropped, preconditions
    )

    exactness_failures = []
    for idx, (rec, out) in enumerate(zip(records, projected)):
        expected_keys = keep_set & set(rec.keys())
        if set(out.keys()) != expected_keys:
            exactness_failures.append(
                f"records[{idx}]: output keys {sorted(out.keys())} != "
                f"keep intersect input {sorted(expected_keys)}"
            )
    proofs.append(
        ProofResult(
            "projection_exactness",
            not exactness_failures,
            (f"all {len(records)} projected records carry exactly "
             "keep_fields intersect input keys"
             if not exactness_failures else "; ".join(exactness_failures)),
        )
    )

    recomputed_dropped = sorted(
        {key for rec in records for key in rec} - keep_set
    )
    disclosure_ok = recomputed_dropped == receipt["fields_dropped"]
    proofs.append(
        ProofResult(
            "drop_disclosure",
            disclosure_ok,
            (("dropped fields fully disclosed: " + ", ".join(fields_dropped))
             if disclosure_ok and fields_dropped
             else ("no fields dropped" if disclosure_ok
                   else f"receipt {receipt['fields_dropped']} != "
                        f"recomputed {recomputed_dropped}")),
        )
    )
    return PrimitiveOutcome(
        output={"records": projected, "mutation_receipt": receipt},
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Mutator 7: geojson_points_to_records
# ---------------------------------------------------------------------------

def geojson_points_to_records(payload: dict) -> PrimitiveOutcome:
    """Flatten a GeoJSON FeatureCollection of Points into flat records.

    payload:
        feature_collection: GeoJSON FeatureCollection whose features are
            all Point geometries with [lon, lat] positions (RFC 7946
            order) and object properties free of 'lat'/'lon' keys

    output:
        records: [{...properties, "lat": <position[1]>,
                   "lon": <position[0]>}, ...]
        coordinate_order: explicit axis-order receipt
        mutation_receipt

    lossiness: lossless (properties carried verbatim; positions become
    named lat/lon fields).

    proofs: schema_validation, geometry_type_gate,
    coordinate_order_receipt, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = [
        "feature_collection_strict_shape",
        "all_geometries_are_points",
        "properties_free_of_lat_lon_keys",
        "positions_read_as_lon_lat",
    ]
    receipt = _mutation_receipt(
        "geojson_points_to_records", "lossless", [], preconditions
    )
    order_receipt = {"geojson_position": "lon,lat", "record_fields": "lat,lon"}

    def degenerate(proofs: list) -> PrimitiveOutcome:
        return PrimitiveOutcome(
            output={
                "records": [],
                "coordinate_order": order_receipt,
                "mutation_receipt": receipt,
            },
            effects_observed=["none"],
            proof_results=proofs,
        )

    errors: list[str] = []
    features: list = []
    fc = payload.get("feature_collection")
    if not isinstance(fc, dict) or fc.get("type") != "FeatureCollection":
        errors.append("'feature_collection' must be a GeoJSON FeatureCollection")
    else:
        extra_members = sorted(set(fc.keys()) - {"type", "features"})
        if extra_members:
            errors.append(
                f"unsupported FeatureCollection members {extra_members} "
                "would be dropped"
            )
        raw = fc.get("features")
        if not isinstance(raw, list):
            errors.append("'feature_collection.features' must be a list")
            raw = []
        for idx, feat in enumerate(raw):
            if not isinstance(feat, dict) or feat.get("type") != "Feature":
                errors.append(f"features[{idx}] must be a Feature object")
                continue
            extra_keys = sorted(
                set(feat.keys()) - {"type", "geometry", "properties"}
            )
            if extra_keys:
                errors.append(
                    f"features[{idx}] unsupported members {extra_keys} "
                    "would be dropped"
                )
            geom = feat.get("geometry")
            props = feat.get("properties")
            if not isinstance(geom, dict):
                errors.append(f"features[{idx}] geometry must be an object")
                continue
            if not isinstance(props, dict):
                errors.append(f"features[{idx}] properties must be an object")
                continue
            for banned in ("lat", "lon"):
                if banned in props:
                    errors.append(
                        f"features[{idx}] properties key {banned!r} would "
                        "collide with the output coordinate field"
                    )
            for key in props:
                if not isinstance(key, str):
                    errors.append(
                        f"features[{idx}] properties has a non-string key {key!r}"
                    )
            if geom.get("type") == "Point":
                coords = geom.get("coordinates")
                if (not isinstance(coords, list) or len(coords) != 2
                        or not all(_is_number(c) for c in coords)):
                    errors.append(
                        f"features[{idx}] Point coordinates must be "
                        "[lon, lat] numbers"
                    )
                    continue
            features.append(feat)
    proofs = [
        ProofResult(
            "schema_validation",
            not errors,
            "; ".join(errors) if errors
            else f"{len(features)} features validated",
        )
    ]
    if errors:
        return degenerate(proofs)

    non_points = [
        f"features[{idx}] geometry type is "
        f"{feat['geometry'].get('type')!r}, not Point"
        for idx, feat in enumerate(features)
        if feat["geometry"].get("type") != "Point"
    ]
    proofs.append(
        ProofResult(
            "geometry_type_gate",
            not non_points,
            (f"all {len(features)} geometries are Point"
             if not non_points else "; ".join(non_points)),
        )
    )
    if non_points:
        return degenerate(proofs)

    records = _records_from_fc(features)

    order_ok = order_receipt == {
        "geojson_position": "lon,lat", "record_fields": "lat,lon",
    }
    for feat, rec in zip(features, records):
        coords = feat["geometry"]["coordinates"]
        if rec["lon"] != coords[0] or rec["lat"] != coords[1]:
            order_ok = False
            break
    proofs.append(
        ProofResult(
            "coordinate_order_receipt",
            order_ok,
            (f"GeoJSON positions read as [lon, lat]; named lat/lon record "
             f"fields verified on {len(records)} records"
             if order_ok
             else "axis-order receipt does not match emitted records"),
        )
    )

    rebuilt = _fc_from_records(records)
    roundtrip_ok = canonical_hash(rebuilt) == canonical_hash(fc)
    proofs.append(
        ProofResult(
            "roundtrip_test",
            roundtrip_ok,
            (f"FeatureCollection of {len(records)} Points reproduced via "
             "records_to_geojson_points inverse"
             if roundtrip_ok
             else "inverse reconstruction diverged from input FeatureCollection"),
        )
    )
    return PrimitiveOutcome(
        output={
            "records": records,
            "coordinate_order": order_receipt,
            "mutation_receipt": receipt,
        },
        effects_observed=["none"],
        proof_results=proofs,
    )


# ---------------------------------------------------------------------------
# Mutator 8: records_to_geojson_points
# ---------------------------------------------------------------------------

def records_to_geojson_points(payload: dict) -> PrimitiveOutcome:
    """Lift flat lat/lon records into a GeoJSON FeatureCollection of Points.

    payload:
        records: list of record objects, each with numeric 'lat' and
                 'lon'; every other field becomes a feature property

    Positions are written in GeoJSON [lon, lat] order (RFC 7946).

    output:
        feature_collection, mutation_receipt

    lossiness: lossless (inverse of geojson_points_to_records).

    proofs: schema_validation, coordinate_range_check, roundtrip_test
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    preconditions = [
        "records_have_numeric_lat_lon",
        "positions_written_as_lon_lat",
        "coordinates_within_wgs84_range",
    ]
    receipt = _mutation_receipt(
        "records_to_geojson_points", "lossless", [], preconditions
    )

    errors: list[str] = []
    records = payload.get("records")
    records_ok = _validate_records(records, errors)
    if records_ok:
        for idx, rec in enumerate(records):
            for key in ("lat", "lon"):
                if not _is_number(rec.get(key)):
                    errors.append(f"records[{idx}] missing numeric {key!r}")
    proofs = [
        ProofResult(
            "schema_validation",
            not errors,
            "; ".join(errors) if errors
            else f"{len(records)} records with numeric lat/lon validated",
        )
    ]
    if errors:
        return PrimitiveOutcome(
            output={"feature_collection": None, "mutation_receipt": receipt},
            effects_observed=["none"],
            proof_results=proofs,
        )

    range_violations = [
        f"records[{idx}] lat={rec['lat']!r} lon={rec['lon']!r} outside "
        "WGS84 range (lat in [-90, 90], lon in [-180, 180])"
        for idx, rec in enumerate(records)
        if not (-90.0 <= rec["lat"] <= 90.0 and -180.0 <= rec["lon"] <= 180.0)
    ]
    proofs.append(
        ProofResult(
            "coordinate_range_check",
            not range_violations,
            (f"all {len(records)} coordinates within WGS84 range"
             if not range_violations else "; ".join(range_violations)),
        )
    )

    fc = _fc_from_records(records)
    rebuilt = _records_from_fc(fc["features"])
    roundtrip_ok = canonical_hash(rebuilt) == canonical_hash(records)
    proofs.append(
        ProofResult(
            "roundtrip_test",
            roundtrip_ok,
            (f"{len(records)} records reproduced via "
             "geojson_points_to_records inverse"
             if roundtrip_ok
             else "inverse reconstruction diverged from input records"),
        )
    )
    return PrimitiveOutcome(
        output={"feature_collection": fc, "mutation_receipt": receipt},
        effects_observed=["none"],
        proof_results=proofs,
    )
