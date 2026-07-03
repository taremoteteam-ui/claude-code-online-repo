# AIDoneRight project template

A ready-to-promote starting point for any AIDoneRight project or system. Copy this
directory's contents to the root of a **new** repository, then delete this line and
fill in the placeholders.

## What you get

```
CLAUDE.md                     agent behavior + the non-negotiable conventions
CONTEXT.md                    the operating manual + living status ledger
STANDARDS.md                  the AIDoneRight standards index (000-004)
.github/workflows/proofs.yml  CI: runs the proof suite on every push
scripts/run_proofs.py         the umbrella proof runner (add your stages here)
schemas/                      JSON schemas — contracts, edited BEFORE any row shape
scripts/seeds/                pure-data seed modules — the ONLY place to edit content
primitives/                   implementations; every run emits a receipt
tests/                        contract tests
```

## First hour

1. Read `STANDARDS.md` — it is short and it is the law.
2. Name your subsystem boundaries as **Globally Unique Names** (Standard 001) and
   drop them in a `guvn`-annotated module so `build_code_map` renders your first
   code map.
3. Find your first **hardcoded choice with more than one reasonable answer** and
   make it a **Multiple-Path Development** portfolio (Standard 002) instead of an
   `if`.
4. Wire `scripts/run_proofs.py` into CI (the workflow is already here) and keep it
   green from commit #1.

## How to promote this to a real template repo

This scaffold lives inside another repository. To make it a standalone template:

```bash
# from a fresh checkout, copy the scaffold out and initialize a repo
cp -r templates/aidoneright-project-template /path/to/new-project
cd /path/to/new-project && git init && git add -A && git commit -m "chore: init from AIDoneRight template"
# then, on your git host, create a new repository and mark it a "template repository"
# (GitHub: Settings -> Template repository) so others can generate from it.
```

Everything here is candidate scaffolding (`serves_truth=false`); replace the
placeholders with your project's real content.
