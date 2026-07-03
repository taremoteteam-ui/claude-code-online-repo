#!/usr/bin/env python3
"""Aggregate improvement work from across the repo into one backlog.

The Primitive Atlas tracks improvement work in several disconnected places:
  * `## Next build slices` sections in `docs/codex/*.md` (hand-authored intent)
  * route-compiler gap records + normalization-candidate queues (measured, from
    the most recent `benchmarks/route_compiler_runs/` run)
  * decision-supervisor tuning recommendations (measured, from
    `benchmarks/decision_runs/supervision_report.json`)

This collector reads them (never writes to any of them) and emits one
`improvement_backlog` object. Like every generated artifact in this repo the
output is `candidate: true, serves_truth: false` - it is a to-do map, not truth.

Stdlib-only, deterministic, and tolerant of missing inputs (empty lists, never
crash).

  python3 scripts/aggregate_backlog.py --self-test   # print JSON, exit 0
  python3 scripts/aggregate_backlog.py --write        # also persist to
                                                      # benchmarks/backlog/backlog.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

DOCS_CODEX_DIR = REPO_ROOT / "docs" / "codex"
ROUTE_RUNS_DIR = REPO_ROOT / "benchmarks" / "route_compiler_runs"
DECISION_RUNS_DIR = REPO_ROOT / "benchmarks" / "decision_runs"
BACKLOG_OUT = REPO_ROOT / "benchmarks" / "backlog" / "backlog.json"

# A "## Next build slices" heading (case-insensitive), tolerating trailing text.
_SLICES_HEADING = re.compile(r"^##\s+next build slices\b", re.IGNORECASE)
# Any level-2 (or deeper) heading terminates the section.
_ANY_HEADING = re.compile(r"^##\s")
# A list item marker: leading whitespace, then either "<digits>." or "-", then
# at least one space. Continuation/wrapped lines do not match and are folded
# into the current item.
_ITEM_MARKER = re.compile(r"^\s*(?:\d+\.|-)\s+(?P<body>.*\S)\s*$")


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    """Parse a .jsonl file into a list of objects; skip blank/unparseable lines."""
    text = _read_text(path)
    if text is None:
        return []
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _read_json(path: Path) -> Any | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _collapse_ws(text: str) -> str:
    return " ".join(text.split())


def extract_doc_slices() -> list[dict[str, Any]]:
    """Scan docs/codex/*.md for '## Next build slices' sections and pull items.

    Each item begins at a number+dot or dash marker; wrapped continuation lines
    are folded into that item. Doc order is sorted by filename (order across
    docs is not meaningful); item order within a doc is preserved (meaningful).
    """
    results: list[dict[str, Any]] = []
    if not DOCS_CODEX_DIR.is_dir():
        return results
    for md_path in sorted(DOCS_CODEX_DIR.glob("*.md")):
        text = _read_text(md_path)
        if text is None:
            continue
        lines = text.splitlines()
        items: list[str] = []
        in_section = False
        current: str | None = None

        def _flush() -> None:
            nonlocal current
            if current is not None:
                items.append(_collapse_ws(current))
                current = None

        for line in lines:
            if not in_section:
                if _SLICES_HEADING.match(line):
                    in_section = True
                continue
            # In-section: a new heading ends it.
            if _ANY_HEADING.match(line):
                _flush()
                in_section = False
                # Only capture the first Next-build-slices section per doc.
                break
            match = _ITEM_MARKER.match(line)
            if match:
                _flush()
                current = match.group("body")
            elif current is not None:
                stripped = line.strip()
                if stripped:
                    current = f"{current} {stripped}"
                else:
                    # Blank line ends the current item (list separator).
                    _flush()
        _flush()

        if items:
            results.append({"doc": md_path.name, "items": items})
    return results


def latest_route_run_dir() -> Path | None:
    """Most recent (lexicographically greatest name) route-compiler run dir."""
    if not ROUTE_RUNS_DIR.is_dir():
        return None
    subdirs = sorted(
        (p for p in ROUTE_RUNS_DIR.iterdir() if p.is_dir()),
        key=lambda p: p.name,
    )
    return subdirs[-1] if subdirs else None


def extract_route_gaps(run_dir: Path | None) -> dict[str, Any]:
    """Wants (unreachable target types) plus compose_rate/gaps from run_summary."""
    section: dict[str, Any] = {
        "source_run": run_dir.name if run_dir is not None else None,
        "wants": [],
        "compose_rate": None,
        "gaps": None,
    }
    if run_dir is None:
        return section

    wants: list[str] = []
    for record in _iter_jsonl(run_dir / "gap_records.jsonl"):
        want = record.get("want")
        if want is not None:
            wants.append(want)
    section["wants"] = wants

    summary = _read_json(run_dir / "run_summary.json")
    if isinstance(summary, dict):
        if "compose_rate" in summary:
            section["compose_rate"] = summary["compose_rate"]
        if "gaps" in summary:
            section["gaps"] = summary["gaps"]
    return section


def extract_normalization_candidates(run_dir: Path | None) -> dict[str, Any]:
    """Count of normalization candidates plus up to 5 sample unmet_type values."""
    section: dict[str, Any] = {
        "source_run": run_dir.name if run_dir is not None else None,
        "count": 0,
        "samples": [],
    }
    if run_dir is None:
        return section
    records = _iter_jsonl(run_dir / "normalization_candidates.jsonl")
    section["count"] = len(records)
    samples: list[str] = []
    for record in records:
        unmet = record.get("unmet_type")
        if unmet is not None:
            samples.append(unmet)
        if len(samples) >= 5:
            break
    section["samples"] = samples
    return section


def extract_open_recommendations() -> list[dict[str, Any]]:
    """kind + from + to for each supervisor tuning recommendation, if present."""
    report = _read_json(DECISION_RUNS_DIR / "supervision_report.json")
    if not isinstance(report, dict):
        return []
    recs = report.get("recommendations")
    if not isinstance(recs, list):
        return []
    out: list[dict[str, Any]] = []
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        out.append(
            {
                "kind": rec.get("kind"),
                "from": rec.get("from_path"),
                "to": rec.get("to_path"),
            }
        )
    return out


def build_backlog() -> dict[str, Any]:
    doc_slices = extract_doc_slices()
    run_dir = latest_route_run_dir()
    route_gaps = extract_route_gaps(run_dir)
    normalization = extract_normalization_candidates(run_dir)
    recommendations = extract_open_recommendations()

    totals = {
        "doc_next_slice_docs": len(doc_slices),
        "doc_next_slice_items": sum(len(d["items"]) for d in doc_slices),
        "route_gaps": len(route_gaps["wants"]),
        "normalization_candidates": normalization["count"],
        "open_recommendations": len(recommendations),
    }

    return {
        "record_type": "improvement_backlog",
        "candidate": True,
        "serves_truth": False,
        "doc_next_slices": doc_slices,
        "route_gaps": route_gaps,
        "normalization_candidates": normalization,
        "open_recommendations": recommendations,
        "totals": totals,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Build the backlog, print it as JSON, and exit 0.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Build the backlog and persist it to benchmarks/backlog/backlog.json.",
    )
    args = parser.parse_args(argv)

    backlog = build_backlog()
    payload = json.dumps(backlog, indent=2, sort_keys=True)

    if args.write:
        BACKLOG_OUT.parent.mkdir(parents=True, exist_ok=True)
        BACKLOG_OUT.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {BACKLOG_OUT.relative_to(REPO_ROOT)}", file=sys.stderr)

    # --self-test (and the default no-arg invocation) print the JSON.
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
