"""Seed data for solution frameworks: reusable typed wiring scaffolds for a
class of problem. Each framework names an input->output contract and the ordered
slots (roles + the canonical type each must produce) that solve it. Filling a
framework binds each slot to a concrete producer in the capability graph; the
deterministic validator gates the result, so a framework composes real
primitives across lanes.

Pure data: one top-level constant FRAMEWORKS. The builder injects record_type,
version, candidate=True, serves_truth=False. Every produces_type here is a real
canonical type produced somewhere in the graph, so the frameworks fill.
"""

FRAMEWORKS = [
    {
        "framework_id": "framework:geo.ingest_tabulate",
        "problem": "Turn a raw GeoJSON point source into a queryable table of rows.",
        "input_edge": "GeoJsonDocument",
        "output_edge": "RowSet",
        "slots": [
            {"role": "parse", "produces_type": "PointFeatureCollection",
             "note": "validate + parse the document into point features"},
            {"role": "flatten", "produces_type": "EntityRecordSet",
             "note": "flatten features into entity records"},
            {"role": "tabulate", "produces_type": "RowSet",
             "note": "pivot records into columns and rows"},
        ],
        "fill_strategies": ["deterministic_compile", "framework_fill", "llm_propose"],
    },
    {
        "framework_id": "framework:auth.login_to_session",
        "problem": "Verify a login attempt and issue a session bearer token.",
        "input_edge": "LoginAttempt",
        "output_edge": "SessionToken",
        "slots": [
            {"role": "verify", "produces_type": "AuthDecision"},
            {"role": "subject", "produces_type": "AuthenticatedSubject"},
            {"role": "issue", "produces_type": "SessionGrant"},
            {"role": "token", "produces_type": "SessionToken"},
        ],
        "fill_strategies": ["deterministic_compile", "framework_fill"],
    },
    {
        "framework_id": "framework:data.csv_to_arrow",
        "problem": "Convert a CSV file into an in-memory Arrow table for analytics.",
        "input_edge": "CsvFile",
        "output_edge": "ArrowTable",
        "slots": [
            {"role": "to_parquet", "produces_type": "ParquetFile"},
            {"role": "to_arrow", "produces_type": "ArrowTable"},
        ],
        "fill_strategies": ["deterministic_compile", "framework_fill"],
    },
]
