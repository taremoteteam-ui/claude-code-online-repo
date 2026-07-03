# Coding-problem primitive mining — solve, decompose, store, reuse

**The request:** scan coding problems (LeetCode / competitive / interview /
hackathon), actually build solutions, break each solution down into primitives,
and store them. **The honest realization** in this offline, no-unmeasured-claims
repo: harvest SYNTHETIC problems shaped like those sources, solve them with real
working code, decompose each solution into reusable algorithmic kernels, verify
both the kernels and the solutions by running them, store them as candidate
cards, and MEASURE the reuse — because reuse is the whole point of an atlas.

## The three layers

1. **Kernels** — `primitives/algorithmic_primitives.py`: 12 real, stdlib-only
   implementations of the classic patterns (two-pointer, sliding-window,
   binary-search-on-answer, prefix-sum, hashing/counting, union-find, BFS, DFS,
   monotonic-stack, Kadane DP, topological-sort, coin-change DP). Each carries a
   self-test fixture.
2. **Solutions** — `primitives/coding_solutions.py`: one working function per
   problem, each **composed from the kernels** (not re-deriving the algorithm),
   and a `uses` list recording the decomposition.
3. **Problems** — `fixtures/coding-problems/problems.json`: 17 synthetic problems
   across the four source styles, each with a paraphrased statement (never copied
   text), a category, its `primitive_uses`, and concrete **test cases**.

## What is measured (live, seeded, honest)

`scripts/run_coding_primitive_pipeline.py` runs every solution against its
fixtures and reports:

- **17 / 17 problems solved**, **34 / 34 test cases passing**, spanning leetcode
  (7), interview (5), hackathon (3), codeforces (2).
- **12 kernels cover 17 problems → reuse factor ≈ 1.42**; the **top-3 kernels
  cover 47% of solved problems**. `counting_frequency` is reused 4×;
  `union_find`, `topological_order`, and `binary_search_answer` 2× each. That is
  the atlas thesis in miniature: a small kernel set assembles many solutions, so
  the next problem is composed from stored parts rather than solved from scratch.

Nothing is asserted — every "solved" is a live run passing that problem's cases.

## Build / check / run

```bash
python3 scripts/build_coding_primitive_pack.py --write     # generate the pack
python3 scripts/check_coding_primitive_pack.py --self-test # schemas + RE-RUN every solution/kernel
python3 scripts/run_coding_primitive_pipeline.py --self-test
python3 -m unittest tests.test_algorithmic_primitives tests.test_coding_solutions
```

The checker is the load-bearing gate: it re-runs every kernel self-test and every
solution against its fixtures from the live code, so a stored card claiming
`verified: true` that no longer runs green goes red. A mutation in the shared
union-find kernel is in the mutation set precisely because it must break every
solution that reuses it.

## Honesty boundary & how it scales

- Problems are `fixture_synthetic`; `source` is a style label; statements are
  original paraphrases. Every card is `candidate: true, serves_truth: false`.
- No "solved N% of LeetCode" claim — only what the checker actually runs is
  reported. Scaling to real problems is a matter of swapping the fixture
  transport for a licensed problem source and letting the same solve → decompose
  → verify → store loop run; the machinery does not change, and the reuse factor
  becomes the metric to watch (it should climb as the kernel library saturates
  the space of patterns).
- The reuse factor and solved counts are protected by the quality ratchet; the
  pack is byte-identical on rebuild (determinism gate).

## Relation to the coding-agent lane

`scripts/seeds/universal_families_coding_agent_seed.py` DESCRIBES the CP solve
loop and lists the algorithm patterns as catalog cards. This lane is the layer
beneath: the patterns as WORKING kernels, with real solved problems proving they
compose. Together they are the "describe the loop / prove the loop solves"
halves of the same story.
