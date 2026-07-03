# Frameworks, LLM-based ordering, and wiring to solve a problem

Last updated: 2026-07-03. The orchestration layer that selects, orders, wires,
validates, and runs primitives to solve a problem — with LLM-based ordering made
safe by a deterministic gate. Builds on the route compiler, adapters, foundry,
graph search, and the decision-portfolio engine.

## The three pieces

### 1. Solution frameworks — reusable typed wiring scaffolds
`schemas/solution_framework.schema.json` + `scripts/seeds/solution_frameworks_seed.py`.
A framework names a problem class as an `input_edge -> output_edge` contract plus
ordered **slots** (a role + the canonical type each must produce). Filling a
framework binds each slot to a concrete producer in the capability graph. The
checker (`check_solution_frameworks_pack.py`) enforces the load-bearing
invariant: **every framework must actually fill and validate against the real
graph** — a scaffold whose slots cannot be bound goes red. Seeded frameworks:
`geo.ingest_tabulate` (GeoJsonDocument→RowSet), `auth.login_to_session`
(LoginAttempt→SessionToken), `data.csv_to_arrow` (CsvFile→ArrowTable).

### 2. Ordering is a portfolio, not one method
`primitives/orderers.py` — there is no single right way to wire primitives, so we
store several and let the shared validator (and receipts) decide:

- **`deterministic_compile`** — the zero-model route compiler's topological order.
- **`framework_fill`** — bind a framework's slots to producers in its wiring
  order (often a *different* valid wiring than the compiler picks — in the demo
  it uses a type adapter for the last step).
- **`llm_propose`** — a model proposes an order; the deterministic
  **`route_validator`** disposes; **`repair()`** topologically fixes an invalid
  proposal. This is the safe way to use an LLM for ordering: **propose freely,
  validate deterministically, run only if it type-checks.** Offline here, a
  labeled stub proposer (0 tokens) deliberately proposes an *invalid* order so
  the validate→repair loop is exercised; a real model plugs into `propose`
  unchanged.

`decision:orchestration.ordering_strategy` (in the decision portfolio) makes the
choice of strategy itself a receipted decision — deterministic-tier by default,
so the cheapest applicable strategy wins until receipts say otherwise.

### 3. The validator is the truth gate
`primitives/route_validator.py:validate_order` checks that any proposed order
type-checks: every step's required inputs are available (from `have` or an
earlier output), and the wanted type is produced — over the same canonical types
the compiler composes on. Whatever proposes the order, this gate is what makes it
trustworthy. A hallucinated wiring is rejected, not run.

## The solve loop (measured, zero model calls)

`scripts/run_solve_demo.py --self-test` solves `GeoJsonDocument -> RowSet`:

```text
RETRIEVE  graph_search -> mined parse_geojson + matched framework geo.ingest_tabulate
CHOOSE    ordering strategy from the portfolio (deterministic-tier -> deterministic_compile)
WIRE      3 strategies, all VALIDATED:
            deterministic_compile: parse -> features_to_records -> records_to_rows   (valid)
            framework_fill:        parse -> features_to_records -> [adapter]rows      (valid, different wiring)
            llm_propose:           stub proposed an INVALID order -> repaired -> valid
EXECUTE   run the chosen valid order on a fixture GeoJSON -> real 2-row table,
            3 ExecutionReceipts
```

So a problem is **retrieved → wired (three ways) → validated → executed**, and
the LLM-ordering path is demonstrably safe: its bad proposal is caught and
repaired before anything runs.

## Honesty

- No model runs here; the LLM proposer is an explicit offline stub (0 tokens).
  The value is the *architecture*: propose → validate → repair, with the
  deterministic gate as the safety boundary. A real model is a drop-in for
  `propose`.
- Every framework/ordering/plan artifact is `candidate=true / serves_truth=false`.
- Frameworks are verified to fill+validate against the real graph; the solve
  demo executes for real and emits receipts. Nothing is asserted that a script
  does not compute.

## Commands

```bash
python3 scripts/build_solution_frameworks_pack.py --write
python3 scripts/check_solution_frameworks_pack.py --self-test   # frameworks fill + validate
python3 scripts/run_solve_demo.py --self-test                   # retrieve -> wire -> validate -> execute
```

## Next build slices

1. Plug a real bounded model into `orderers.llm_propose`'s `propose` slot in a
   model-enabled environment; keep the validator/repair gate — measure how often
   the model's proposal validates first-try vs needs repair.
2. Grow the framework catalog per lane (SWE repair, RAG cite, detect-and-crop,
   dbt medallion) and let `framework_fill` compete with `deterministic_compile`
   on receipts.
3. Wire the ordering-strategy decision into the solve loop's execution path so
   the chosen strategy is recorded and the supervisor can promote the winner.
