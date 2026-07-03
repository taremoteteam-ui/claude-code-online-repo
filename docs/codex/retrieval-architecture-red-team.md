# Red-team: aggressively challenging the storage, search, and matching architecture

Last updated: 2026-07-03. A deliberately adversarial audit of how this repo
ACTUALLY stores, searches, ranks, remixes, and composes primitives — versus what
`docs/codex/multi-path-flexible-primitive-architecture.md` claims. Every charge
below is backed by a code read or a measurement run in this repo, not opinion.
Companion/target of the critique: that architecture doc's Sections 1–4.

> Stance: the vision is right; the *implemented substrate is far thinner than the
> vision reads*, and a few thin spots are load-bearing. This document names them,
> proves them, ranks them, and specifies the fix. One fix (universal retrieval)
> is already built and measured here as proof the critique is actionable.

---

## 0. Method

- Read the only retrieval code that exists: `primitives/search.py`
  (`PackSearchIndex`, `candidate_bundle_search`) and `primitives/route_compiler.py`.
- Ran probes over the real artifacts (2,867-node capability graph, all pack
  manifests). Probe outputs are quoted inline.
- Where a charge is fixed, the fix ships with a measured before/after and a
  proof stage in `scripts/run_proofs.py`.

---

## 1. Headline verdict

The "search 113k+ primitives across a portfolio of paths" story has, in this
repo, been **one lexical index over 1.74% of the universe, with one ranking
signal, no semantic plane, no blocking keys, no prompt→intent bridge, and a
self-congratulatory 1.0 eval measured on its own training pack.** The route
compiler is genuinely good and honest; everything UPSTREAM of it (how you get
from a human intent to the typed `(have, want)` it needs) was essentially
unbuilt. That upstream gap is the single most important thing to attack.

Scorecard of the claims vs reality:

| # | Architecture-doc claim | Reality in this repo (evidence) | Severity |
|---|---|---|---|
| 1 | "~113k+ primitives stay searchable" | The only index covered **50 of 2,867 nodes = 1.74%**; hard-coupled to the place-discovery row schema, **crashes** opening any other lane | Critical |
| 2 | "Search: exact · type · BM25 · dense vector · hybrid RRF · graph route …" (a portfolio) | **One** path: home-grown lexical IDF over 5 concatenated fields. No BM25, no vectors, no RRF, no graph-route search | Critical |
| 3 | "retrieval quality is MEASURED" → 1.0 recall | 1.0 is over the **~50-doc place-discovery pack with questions co-authored for it**, zero cross-lane distractors. Honest cross-lane hit@5 is **0.667** | High |
| 4 | "Multi-embedding profiles … edge_io / blackbox / failure_mode vectors" | **Zero** embeddings anywhere. No vector, no `embedding_port`, no profile registry in this repo | High |
| 5 | "Key blocks / blocking_keys prune the universe in one hop" | **No `blocking_keys` column exists on any row**; search is a full linear scan | High |
| 6 | "Data chooses by receipts over the co-occurrence graph" (multi-signal ranking) | Ranking = lexical score × 1.25 group boost. Proof/risk/reuse/co-occurrence/negative-memory **do not enter the score**; negative memory only appends warnings | High |
| 7 | "prompt → decompose → search → compose" one loop | Search returns IDs from prose over pack A; the compiler consumes typed `(have,want)` over graph B. **Nothing converts a prompt into `(have,want)`, and the two operate on different corpora.** The loop is not connected | Critical |
| 8 | "LLM peels back layers only if necessary (L1→L7)" | A concept with **no mechanism**. Groups declare `hidden_member_edges` but nothing decides to open them on demand | Medium |
| 9 | Typed edges make routes compose | True, but matching is **binary** (exact \| reviewed-synonym \| adapter). No graded/semantic type compatibility; any unknown near-name type silently gaps until a human edits `_SYNONYM_MAP` | High |
| 10 | Generated content is trustworthy candidate material | Structural checkers pass content that is **semantically wrong**: `prim:mset.except` declares `output_edge … -> UnionedRecordSet` (an EXCEPT yields a *difference*, not a union). No checker catches it | Medium |
| 11 | Stable, canonical ids | **Namespace is unenforced across authoring paths**: the multiset lane exists as `prim:mset.*`/`prim:sem.*` (workflow) where the hand-authored convention was `prim:multiset.*`/`prim:semantic.*`. Retrieval-by-id and cross-refs are fragile | Medium |

---

## 2. The charges in detail (with evidence)

### C1 / C2 — one index, 1.74% coverage, hard-coupled (CRITICAL)
`PackSearchIndex.__init__` reads `pack_dir/primitive_cards.jsonl` and
`primitive_groups.jsonl` and indexes `card["primitive_id"]`,
`row["blackbox"]["does"]`, `row["lane"]`. Those fields exist only in the
place-discovery pack. Probe:

```text
capability graph nodes: 2867
what the search index indexes: 38 cards + 12 groups = 50 docs
coverage of the universe: 1.74%
index a different lane -> FileNotFoundError: .../universal-primitive-catalog/primitive_cards.jsonl
coding prompt 'generate a patch that fixes the failing test' -> []   (SWE lane unreachable)
```

The universal catalog (1,271 resolved), warehouse (976 + 54 templates + 28
pipelines), the coding lane, and the adapters are **not retrievable by any code
in the repo**. They are only *compilable* if a caller already knows the exact
typed `(have, want)`.

### C3 — the 1.0 recall is an echo test (HIGH)
`scripts/evaluate_candidate_search.py` sets `PACK_DIR = …/place-discovery-…`,
searches only that pack, and scores `directed_question` (written alongside the
primitives) against their own `primitive_demands`. There are no distractors from
other lanes and the query vocabulary overlaps the card vocabulary by
construction. 1.0 there says almost nothing about universe-scale retrieval. The
honest cross-lane number (below) is **0.667**.

### C4 / C5 — no semantic plane, no blocking keys (HIGH)
There is no embedding of any kind and no `blocking_keys` field on any schema.
The doc's Section 3 (multi-embedding profiles, LSH blocking, RRF fusion) is
entirely aspirational here. At 2,867 nodes a linear lexical scan is fine; at the
claimed scale it is neither fast nor precise, and there is nothing to prune on.

### C6 — single-signal ranking (HIGH)
`PackSearchIndex.score` = Σ idf·(1+log tf) / √len × (1.25 if group). Proof
status, risk class, reuse/co-occurrence, freshness, and negative memory are all
absent from the score. `candidate_bundle_search` loads negative memory only to
append *warnings*, never to demote a hit. "Data chooses by receipts" is not
implemented in the ranker.

### C7 — the prompt→intent bridge is missing (CRITICAL)
This is the big one. The compiler is excellent but its input is
`compile_route(have: list[str], want: str, …)` — canonical *type names*. Nothing
turns "fix the failing test in this repo" into `have=[IssueText, RepoSnapshot],
want=ValidatedPatch`. And search (prose→ids over pack A) and compile (types→plan
over graph B) don't share a corpus or a hand-off object. The advertised loop
`intent → search → compose` has no wire between the first arrow's output and the
second arrow's input.

### C8 — layer-peeling is a slogan (MEDIUM)
Groups carry `hidden_member_edges` (≥3, verified), but no code path decides
"open this doll because the route needs a member edge." L1→L7 context depth is
described, never executed.

### C9 — binary type matching won't scale (HIGH)
`canonical_type(name)` returns the name unless it's one of ~14 reviewed synonyms.
So `WebhookHttpRequest` vs `ProviderWebhook` gaps until a human adds a synonym or
an adapter. That is correct and honest at today's scale — but it makes
composability a function of *manual curation throughput*. With thousands of
ad-hoc port names across mined repos, the normalization queue becomes the
bottleneck. There is no graded compatibility (embedding-near types, structural
subtyping) to propose high-confidence links automatically for review.

### C10 / C11 — structural checkers miss semantic + namespace errors (MEDIUM)
`prim:mset.except` (workflow-authored) declares `output_edge = … +
UnionedRecordSet` — an EXCEPT/MINUS produces a *difference*, and the family's own
prose says so, yet the typed output is a union. The pack checker is green
because it validates structure, not meaning. Separately, the same lane shipped as
`prim:mset.*`/`prim:sem.*` when the hand-authored convention was
`prim:multiset.*`/`prim:semantic.*` — nothing enforces one namespace, so a
cross-reference or an id-based retrieval can silently target the wrong or a
nonexistent id.

---

## 3. What GOOD looks like (the redesign this argues for)

A retrieval/storage model that actually scales and connects to the compiler:

1. **One universal index over the capability graph, lane-agnostic.** Index every
   node by uniform fields; never couple to a pack's row schema. *(built — §4)*
2. **A columnar document per primitive with real blocking keys.** Add
   `blocking_keys[]` (output canonical types, lane, capability tags, coarse
   LSH bucket) so a typed query prunes to a small block before scoring. Store the
   many search columns the doc describes as actual fields, not prose.
3. **A semantic plane.** Named embedding profiles (`edge_io`, `blackbox`,
   `problem`, `failure_mode`) with a deterministic lexical floor and an optional
   local vector model, fused by RRF. This is what closes the vocabulary gap that
   makes today's lexical index miss "keeping every row" → `union_all`.
4. **Multi-signal ranking.** Fuse lexical + typed-edge-truth + proof status +
   risk + co-occurrence reuse + negative-memory demotion into one score, each
   term disclosed in `ranking_explanation`.
5. **The prompt→intent bridge (highest priority).** A component that maps a
   natural-language task to `(have, want)` canonical types — deterministic
   pattern lanes first, a bounded model only for the ambiguous slot — so
   search-hits become compiler input. This is the missing wire in the loop.
6. **Graded type compatibility with disclosure.** Beyond exact/synonym/adapter,
   propose embedding-near or structurally-compatible type links as *candidate*
   synonyms/adapters for review — turning the normalization queue from manual
   backlog into a ranked, auto-populated worklist.
7. **Layer-peel on demand.** When a route needs an edge only a group's member
   exposes, open that group (and only then) — an explicit escalation, receipted.
8. **A semantic content gate.** A checker lane that flags obvious contract
   contradictions (an EXCEPT outputting a union; an idempotent op without an
   idempotency proof; input/output type disagreeing with the prose) — catching
   the C10 class the structural checker cannot.
9. **A canonical namespace/lint pass** so `mset`/`multiset` can't both exist.

---

## 4. What this pass already FIXED (measured, not promised)

Attacking C1/C2/C3 directly, this pass shipped a universal retrieval index and
an honest cross-lane eval:

- **`primitives/graph_search.py` — `GraphSearchIndex`**: indexes **all 2,867**
  capability-graph nodes lane-agnostically, with two planes — lexical IDF AND
  typed-edge blocking keys (`producers_by_type` / `consumers_by_type`). A query
  can name a wanted output type to PRUNE to the nodes that actually produce it,
  then rerank lexically. The coding prompt that returned `[]` now returns:

  ```text
  prim:swe.generate_patch     planes=[lexical]
  prim:swe.validate_patch     planes=[lexical, produces_want]
  ```

- **`scripts/evaluate_graph_search.py` — honest cross-lane eval**: 15 paraphrased
  intents (avoiding verbatim titles) over the FULL graph (every other lane is a
  distractor). Measured, not tuned:

  ```text
  corpus_nodes: 2867          (vs 50 before)
  lexical_only         hit@5 = 0.667   mrr = 0.58
  lexical + typed-edge hit@5 = 0.667   mrr = 0.633   (typed plane lifts RANK, not recall, on this set)
  ```

  The 0.667 is the point: it exposes the vocabulary brittleness the old 1.0
  hid. The misses are exactly the semantic-gap cases ("combine two record sets
  keeping every row" misses `mset.union`; "missing from the second" misses
  `mset.except`) — the evidence that a semantic plane (redesign item 3) is the
  next real win, not a nice-to-have. Wired as a `run_proofs.py` stage that gates
  on full-graph coverage and typed-plane-does-not-hurt-recall.

This does NOT close C4–C11. It converts the biggest lie (retrieval exists at
scale) into a true, measured floor to improve from.

---

## 5. Prioritized build order (attack the load-bearing gaps first)

1. **Prompt→intent bridge (C7)** — without it the whole loop is disconnected;
   everything else is polishing a component nobody can reach from a prompt.
2. **Semantic plane + RRF fusion (C4)** — the measured 0.667 says lexical alone
   leaves a third of cross-lane intents unreachable; embeddings are the fix with
   the clearest evidence behind it.
3. **Multi-signal ranking (C6)** — fold proof/risk/co-occurrence/negative-memory
   into the score so "data chooses" becomes literally true.
4. **Blocking keys as real columns (C5)** — required before scale, cheap to add.
5. **Semantic content gate (C10) + namespace lint (C11)** — stop shipping
   contradictory/duplicate content while volume grows.
6. **Graded type compatibility (C9)** and **layer-peel-on-demand (C8)** — the
   scale-out items once the loop is connected and honest.

The through-line: the system's *composition* substrate (typed edges, route
compiler, adapters) is real and honest; its *retrieval and intake* substrate was
mostly narrative. Fix retrieval and the prompt bridge, and the composition engine
finally has something to compose from at scale.
