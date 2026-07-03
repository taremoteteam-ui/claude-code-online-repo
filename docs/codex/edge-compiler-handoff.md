# Edge Compiler Handoff: compiling primitive graphs by their edges

Last updated: 2026-07-03

Audience: Claude Code, Claude Code Fable, Codex, and agents building the route
compiler.

Status: working deterministic compiler + measured demo. All rows are
candidate=true / serves_truth=false. Compose rates and gap queues are computed
from local runs; recompute from the run manifests.

## The goal this serves

The primitive bank only pays off if a task can be built by REORDERING and
CONNECTING primitives by their edge compatibility - not by reading each
primitive's internals or rewriting large code blocks. An LLM (or plain
deterministic search) should look at input/output edges, find a chain whose
types connect, and "compile" a graph execution. This lane makes that concrete.

## What was built

1. `primitives/edges.py` - the typed port model. Every port in an edge string
   (`TypeA+TypeB+Policy`) gets a deterministic role and canonical type:
   - role `config` (Policy/Spec/Context/Weights suffix): supplied by the
     compile REQUEST, so it never blocks composition.
   - role `receipt` (Receipt/Report/... suffix): evidence output.
   - role `data`: an artifact that must be produced upstream or provided.
   - `canonical_type`: **conservative** - a port's own name by default, so
     genuinely-distinct artifacts never silently merge (a MapArtifact is not a
     MockServerArtifact). Type equivalences live in a curated, REVIEWED
     `_SYNONYM_MAP`; expanding it is promotion-gated work, and every non-exact
     hop the compiler makes is labeled `typed`, never hidden.

2. `scripts/build_capability_graph.py` - turns every primitive across all lanes
   (place-discovery cards + groups, universal families + resolved primitives,
   document-extraction primitives) into one typed graph node with its data
   inputs, config ports, and outputs. Emits `capability_graph.jsonl` +
   `port_type_index.jsonl` (which types are produced/consumed by which nodes).

3. `primitives/route_compiler.py` - the deterministic compiler.
   `compile_route(have, want, nodes)` forward-chains over canonical types (a
   node runs when all its data inputs are available; config ports are free),
   then reconstructs a minimal, topologically ordered PlanLock with a stable
   `route_hash`. Zero model calls. Unreachable targets return a gap carrying
   the unmet type and nearest producers.

4. `scripts/run_route_compiler_demo.py` - compiles a curated set of realistic
   `(have -> want)` targets, persists the PlanLocks, the gap records, and a
   port-normalization-candidate queue, and reports the compose rate honestly.

## What the measurement shows (recompute from the run manifest)

The demo composes a meaningful fraction of targets with zero model calls,
including genuine multi-step chains built from edges alone, for example:

```text
CsvFile -> [csv_to_parquet] -> ParquetFile -> [parquet_to_arrow] -> ArrowTable
   (2 steps, every hop EXACT tier: connected by identical port names)

AreaOfInterest -> [hrsa_health_center_ingester] -> EntityRecordSet
               -> [entity_normalize_and_dedupe] -> CanonicalEntitySet
   (2 steps; the hop is TYPED tier via a reviewed synonym, and labeled so)
```

The honest finding: composition works cleanly where the bank uses a consistent
port vocabulary (format conversion, entity resolution, data quality), and
GAPS appear where primitives were authored with lane-local descriptive names
that don't yet share a canonical type. That is the actionable path to tens of
thousands of *composable* primitives:

```text
gap -> normalization candidate (which distinct port names denote the same
       artifact and should be declared synonymous under review)
    OR connector demand (which small adapter/mutator primitive is missing to
       bridge two real types)
```

Both are emitted by the demo. The compiler is the mechanism; port-vocabulary
normalization and connector primitives are the growth work it points at.

## The compatibility contract (what an LLM reads instead of code)

To compose two primitives, only their edges matter:

```text
P1.output_ports  ⊇(by canonical_type)  P2.required_input_ports
```

- exact tier: an output port name equals an input port name.
- typed tier: they share a canonical type via a reviewed synonym.
- config ports (P2's policies) are the caller's to supply.

No internals are read. The PlanLock records every connection, its tier, and
which upstream step (or the request) satisfied it - fully auditable.

## Repo pointers

```text
primitives/edges.py                        typed port model + reviewed synonym map
primitives/route_compiler.py               deterministic edge compiler
schemas/capability_graph_node.schema.json
schemas/compiled_route.schema.json
scripts/build_capability_graph.py --self-test
scripts/run_route_compiler_demo.py --self-test | --write
catalog/knowledge-packs/data/capability-graph/manifest.json   (recompute counts)
benchmarks/route_compiler_runs/<id>/                          (PlanLocks + gaps + norm queue)
```

## Next build slices

1. Grow the reviewed `_SYNONYM_MAP` from the normalization-candidate queue -
   each accepted equivalence unlocks more multi-step chains. This is the
   highest-leverage way to raise the compose rate.
2. Connector/adapter primitives for the highest-demand gaps (the demo's
   nearest-producer hints name them) - e.g. an `entity_records_to_point_set`
   adapter to bridge resolution and spatial lanes.
3. Wire `primitives/mutators.py` in as ADAPTER EDGES: a deterministic mutator
   (field_rename, json_to_rows) can bridge two near-miss ports, so the compiler
   inserts a mutator step instead of declaring a gap.
4. Execute a compiled PlanLock end to end for a lane where working primitives
   exist (place-discovery), proving the compiled route runs, not just composes.
5. An LLM-in-the-loop arm: give the model only the compact edge cards + the
   compiler, and measure task success vs a baseline that reads source - the
   first direct test of "compile by edges beats rereading code".
