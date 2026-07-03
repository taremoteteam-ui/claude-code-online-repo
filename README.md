# Primitive Atlas

### A universal catalog of every type of programming primitive — and the fully flexible, unlimited-possibility path & runtime engine(s) that search, compose, choose, and run them.

Two co-equal pillars:

1. **Primitive Atlas** — a searchable, edge-typed catalog of reusable
   capabilities across **every domain** (auth, security, CRUD, data engineering,
   warehouse/dbt/analytics, integration, devops, guardrails, entity resolution,
   enrichment, document extraction, RAG, media/vision, coding-agent
   (SWE-bench-style), competitive programming, classic algorithms, set algebra,
   semantic layers, geospatial, …). Every capability is a black box with a
   compact typed contract, so an LLM (or plain search) composes large programs by
   **ordering primitives on their input/output edges — reading contracts, not
   implementations.**
2. **The flexible path & runtime engine(s)** — route compiler, decision-portfolio
   engine, universal graph search, deterministic remix/adapters, and
   receipt-driven execution — that turn the catalog into composed, proven
   programs. The governing law is **non-commitment**: never hardcode one method;
   store the space of paths as data and let receipts choose the best path (or
   paths) per situation. Nothing commits to a single pipeline, model, prompt,
   search method, or storage engine.

Place-discovery/geospatial was the first lane; the architecture is not specific
to it. **Any primitive type — and any decision — joins as data (a row / a new
seed lane), never a rewrite**, all crossing the same typed capability graph and
the same domain-agnostic engines.

Core sentence:

```text
Search first. Reuse first. Remix deterministically. Generate only the missing
edge. Prove every route. Promote only after receipts. Remember failures as
negative memory.
```

## Status — everything here is candidate seed material

```json
{ "candidate": true, "serves_truth": false }
```

No primitive here is promoted to truth. Nothing is source-backed until a real
implementation runs through `primitives/core.py`, emits an ExecutionReceipt, and
clears its proof obligations. **No real-world accuracy, speed, cost, or
token-savings metric is claimed anywhere** — the only measured numbers are
machinery metrics (compose rate, retrieval hit rate, proof-suite pass) computed
by the scripts below, and fixture-mode runs disclose that they measure route
machinery, not real data. Counts come from each pack's `manifest.json` —
recompute, never hand-type them.

## What is built now (recompute counts from each pack manifest)

| Lane / layer | Pack | Shape |
| --- | --- | --- |
| **Universal catalog** | `universal-primitive-catalog/` | base families × runtime wrappers → resolved primitives across auth/identity, security, crud, data, integration, devops, observability, guardrails, entity-resolution, enrichment, document-intelligence, RAG, similarity, media/image/vision, API-integration, **coding-agent (`prim:swe.*`)**, **competitive-programming (`prim:cp.*`)**, **algorithms (`prim:algo.*`)** |
| **Warehouse / analytics** | `warehouse-analytics-catalog/` | dbt, dimensional modeling (incl. SCD), data engineering, analytics patterns, semantic layer, multiset/set-algebra families + slot templates + multi-wave pipelines (topological wave contract enforced) |
| **Document extraction** | `document-extraction-seeds/` | (doc_type × field) target lattice for contract/PDF/word extraction with the source-span grounding invariant |
| **Place discovery / geospatial** | `place-discovery-geospatial-seeds/` | the reference lane: primitive cards, groups, variation overlays, source surfaces, benchmark task demands (see boundaries below) |
| **Type adapters** | `type-adapters/` | reviewed deterministic `FromPort→ToPort` connectors, backed by real code + proofs, registered as graph nodes so the compiler bridges near-matches |
| **Decision portfolios** | `decision-portfolios/` | the domain-agnostic "store all paths, let data choose" substrate (decision points, execution paths, receipt ledger, self-tuning supervisor) |
| **Capability graph** | `capability-graph/` | one typed node per primitive across every lane + the port-type producer/consumer index — the substrate the route compiler and universal search traverse |

Every row is `candidate=true / serves_truth=false`. The domain enum already spans
30+ primitive domains; adding another is a seed module, not an architecture
change.

## The flexible path & runtime engine(s) (what makes it a market, not a list)

Domain-agnostic engines that search, compose, choose, remix, and run primitives —
no engine is specific to a lane, and none commits to a single method:

- **Edge compiler** (`primitives/route_compiler.py`, `scripts/run_route_compiler_demo.py`):
  forward-chaining route assembly over the typed capability graph with **zero
  model calls** — connects primitives by canonical-type compatibility, labels
  every hop `exact` / `typed` / adapter, and emits a hashable, replayable
  PlanLock or an honest gap. Compose rate + gap queue are measured, recompute
  with the demo.
- **Type-adapter connectors** (`primitives/type_adapters.py`): deterministic
  reshapes that let the compiler bridge a near-match instead of leaving a gap,
  each disclosed as an explicit adapter step.
- **Universal graph search** (`primitives/graph_search.py`,
  `scripts/evaluate_graph_search.py`): lane-agnostic retrieval over the whole
  graph with two planes — lexical + typed-edge blocking keys — measured by an
  honest cross-lane eval (paraphrased intents, every other lane a distractor).
- **Decision-portfolio engine** (`primitives/decision_engine.py` +
  `decision_supervisor.py`): generalizes the non-commitment law — store the
  space of paths as data, keep selection as a policy over an append-only receipt
  ledger; a self-tuning supervisor emits promote/retire/reopen recommendations.

## Read first

- [`docs/BIBLE.md`](docs/BIBLE.md) — the north-star reference.
- [`docs/codex/primitive-atlas-northstar.md`](docs/codex/primitive-atlas-northstar.md) — mission brief + operating loop.
- [`docs/codex/compiled-primitive-routes-handoff.md`](docs/codex/compiled-primitive-routes-handoff.md) — compiled-route architecture + the non-commitment principle.
- Lane handoffs: coding-agent, document-extraction, warehouse, place-discovery, type-adapters, and the [decision-portfolio substrate](docs/codex/decision-portfolio-substrate.md).
- [`docs/codex/multi-path-flexible-primitive-architecture.md`](docs/codex/multi-path-flexible-primitive-architecture.md) and [`docs/codex/retrieval-architecture-red-team.md`](docs/codex/retrieval-architecture-red-team.md) — the multi-path vision and its honest, evidence-based critique.

## Non-negotiable conventions

1. Generated packs come from builder scripts — never hand-edit files under
   `catalog/knowledge-packs/data/`. Edit the seed modules in `scripts/seeds/` or
   the builder, then regenerate. The checker's content-hash gate fails on
   hand-edited pack files.
2. Every generated row is `candidate=true / serves_truth=false`.
3. Counts come from `manifest.json` only.
4. Schemas before data: update `schemas/*.schema.json` before changing row shapes.
5. No unmeasured performance, savings, or benchmark claims anywhere.
6. IDs are stable and version-free; versions live in the `version` metadata field.

## Commands

```bash
# Everything at once (CI runs this on every push): builders, checkers, unit
# tests, capability graph, route compiler, retrieval evals, decision engine.
python3 scripts/run_proofs.py
```

Per-lane build/check commands and the full command list live in
[`CLAUDE.md`](CLAUDE.md). The builder is the single source for every pack file.

## Reference lane boundaries (place-discovery / geospatial)

The first lane carries domain compliance boundaries that any similarly-regulated
lane must mirror:

- Directory / access / planning outputs only — never patient-level data, never
  diagnosis or treatment advice, never final legal or compliance conclusions.
- Respect source usage policies and attribution (e.g. OSM ODbL); scaled use must
  self-host or use bulk extracts.
- Every ingest records license status, attribution, and a source snapshot
  receipt; every spatial analysis records a method receipt.

See [`docs/codex/place-discovery-compliance-and-policy.md`](docs/codex/place-discovery-compliance-and-policy.md)
for the full promotion gates.

## Next build slices

1. **Live source capture** for lanes with real sources: run adapters through
   `LiveTransport` so receipts flip from `fixture_offline` to `live_network`.
2. **Baseline arms**: wire model-in-the-loop runs (incl. the SLM-uplift
   benchmark in the coding-agent lane) so the first measured token/accuracy
   comparisons exist — until then no savings claim is made.
3. **Retrieval upgrades**: the prompt→(have,want) bridge and a semantic
   embedding plane against the measured cross-lane floor (see the red-team doc).
4. **Storage tiers**: extract a `StoragePort` so the in-memory/JSONL substrate
   scales to embedded (DuckDB) → server (Postgres+OLAP) → graph-native without
   changing the engines.
5. **Promotion pipeline**: first held-out promotion gate over implemented
   primitives (candidate → source-backed with receipts).
