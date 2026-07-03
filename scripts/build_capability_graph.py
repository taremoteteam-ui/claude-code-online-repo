#!/usr/bin/env python3
"""Builder for the primitive capability graph.

Reads every primitive-bearing pack across all lanes and emits one typed node
per primitive: its edges parsed into typed ports (data inputs needed upstream,
config ports supplied by the request, output ports produced). The route
compiler traverses these nodes to assemble chains by port-type compatibility
alone - never reading a primitive's internals.

Single source for catalog/knowledge-packs/data/capability-graph/. Counts and
hashes in manifest.json are computed. Every row candidate=true/serves_truth=false.

Usage:
    python3 scripts/build_capability_graph.py --self-test
    python3 scripts/build_capability_graph.py --write
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from primitives.edges import config_ports, output_ports, required_input_ports  # noqa: E402

PACK_ROOT = REPO_ROOT / "catalog" / "knowledge-packs" / "data"
OUT_DIR = PACK_ROOT / "capability-graph"

PACK_ID = "capability-graph"
PACK_VERSION = "0.1.0"
ROW_VERSION = "0.1.0"
GENERATED_BY = "scripts/build_capability_graph.py"

# (pack file, id field, lane, kind field or literal). Every primitive-bearing
# row in the bank contributes one node.
SOURCES = [
    ("place-discovery-geospatial-seeds/primitive_cards.jsonl",
     "primitive_id", "place_discovery", "kind"),
    ("place-discovery-geospatial-seeds/primitive_groups.jsonl",
     "group_id", "place_discovery", None),
    ("universal-primitive-catalog/primitive_families.jsonl",
     "family_id", "universal", None),
    ("universal-primitive-catalog/resolved_primitives.jsonl",
     "resolved_id", "universal", None),
    ("document-extraction-seeds/extraction_primitives.jsonl",
     "primitive_id", "document_extraction", "kind"),
]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def node_from_row(row: dict, id_field: str, lane: str, kind_field) -> dict:
    node_id = row[id_field]
    in_edge = row["input_edge"]
    out_edge = row["output_edge"]
    kind = row.get(kind_field, "primitive") if kind_field else row.get("record_type", "primitive")
    title = row.get("title", node_id)
    effects = list(row.get("effects", []))
    return {
        "record_type": "capability_graph_node",
        "node_id": node_id,
        "lane": lane,
        "kind": kind,
        "title": title,
        "input_edge": in_edge,
        "output_edge": out_edge,
        "required_input_ports": [{"name": p.name, "canonical_type": p.canonical_type}
                                 for p in required_input_ports(in_edge)],
        "config_ports": [{"name": p.name, "canonical_type": p.canonical_type}
                         for p in config_ports(in_edge)],
        "output_ports": [{"name": p.name, "role": p.role, "canonical_type": p.canonical_type}
                         for p in output_ports(out_edge)],
        "effects": effects,
        "version": ROW_VERSION,
        "candidate": True,
        "serves_truth": False,
    }


def build_nodes() -> list[dict]:
    nodes: dict[str, dict] = {}
    for rel, id_field, lane, kind_field in SOURCES:
        for row in load_jsonl(PACK_ROOT / rel):
            if "input_edge" not in row or "output_edge" not in row:
                continue
            node = node_from_row(row, id_field, lane, kind_field)
            nodes[node["node_id"]] = node
    return sorted(nodes.values(), key=lambda n: n["node_id"])


def build_port_index(nodes: list[dict]) -> list[dict]:
    """canonical_type -> which nodes produce it / consume it (as a data input)."""
    produced: dict[str, set] = {}
    consumed: dict[str, set] = {}
    for n in nodes:
        for p in n["output_ports"]:
            produced.setdefault(p["canonical_type"], set()).add(n["node_id"])
        for p in n["required_input_ports"]:
            consumed.setdefault(p["canonical_type"], set()).add(n["node_id"])
    types = sorted(set(produced) | set(consumed))
    return [{
        "record_type": "capability_port_type",
        "canonical_type": t,
        "producer_count": len(produced.get(t, set())),
        "consumer_count": len(consumed.get(t, set())),
        "producers": sorted(produced.get(t, set()))[:25],
        "consumers": sorted(consumed.get(t, set()))[:25],
        "candidate": True,
        "serves_truth": False,
    } for t in types]


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(r, ensure_ascii=True) + "\n" for r in rows).encode("utf-8")


def build_pack() -> dict[str, bytes]:
    nodes = build_nodes()
    port_index = build_port_index(nodes)
    files = {"capability_graph.jsonl": nodes, "port_type_index.jsonl": port_index}
    payloads = {name: jsonl_bytes(rows) for name, rows in files.items()}
    manifest = {
        "pack_id": PACK_ID,
        "pack_version": PACK_VERSION,
        "generated_by": GENERATED_BY,
        "schema_refs": ["schemas/capability_graph_node.schema.json",
                        "schemas/pack_manifest.schema.json"],
        "files": {name: {"rows": len(files[name]),
                         "content_sha256": hashlib.sha256(payloads[name]).hexdigest()}
                  for name in sorted(files)},
        "row_counts": {name: len(rows) for name, rows in sorted(files.items())},
        "total_rows": sum(len(rows) for rows in files.values()),
        "candidate": True,
        "serves_truth": False,
    }
    payloads["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    return payloads


def self_test() -> int:
    payloads = build_pack()
    manifest = json.loads(payloads["manifest.json"])
    nodes = [json.loads(x) for x in payloads["capability_graph.jsonl"].decode().splitlines()]
    problems = []
    if not nodes:
        problems.append("no capability graph nodes built")
    for n in nodes:
        if n["candidate"] is not True or n["serves_truth"] is not False:
            problems.append(f"{n['node_id']}: boundary violated")
            break
    if problems:
        print(json.dumps({"ok": False, "problems": problems}, indent=2))
        return 1
    print(json.dumps({"ok": True, "self_test": "capability_graph",
                      "row_counts": manifest["row_counts"], "total_rows": manifest["total_rows"]}))
    return 0


def write_pack() -> int:
    payloads = build_pack()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in sorted(payloads.items()):
        (OUT_DIR / name).write_bytes(data)
    manifest = json.loads(payloads["manifest.json"])
    print(json.dumps({"ok": True, "pack_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
                      "row_counts": manifest["row_counts"], "total_rows": manifest["total_rows"]},
                     indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if args.write:
        return write_pack()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
