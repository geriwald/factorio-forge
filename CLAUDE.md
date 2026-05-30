# CLAUDE.md — factorio-forge

Project-specific guidance. Global rules (Les Tables de Claude, TDD, Conventional
Commits, Gitflow) still apply; this file only records what is **not** derivable
from the code, the README, or git history.

## What this project is

A research project testing whether LLM-driven quality-diversity search (autoresearch
pattern + FunSearch/AlphaEvolve lineage + MAP-Elites) can make **non-canonical**
Factorio production structures emerge. Full framing: [`docs/design.md`](docs/design.md)
— read it before any non-trivial change. The design doc is the durable contract;
this CLAUDE.md is operational guidance.

The canonical, living version of the design doc is in French in the brain vault
(`~/brain/research/factorio-autoresearch-structures-emergentes.md`); `docs/design.md`
here is the English snapshot. If the design evolves, update the French source and
regenerate the English snapshot — do not let them silently diverge.

## Architecture in one breath

Three nested regimes (artisanal naming, keep it): **Workshop** (one block, steady
state, idealized I/O) → **Workbench** (best block given unlocked tech) → **Campaign**
(full from-zero trajectory). Linked by the **Catalog** (measured block contracts).
Central object = a git-versioned **MOME** (Multi-Objective MAP-Elites) elite archive,
objective-agnostic: any objective can be the session's lead, others recorded for info.

## The one thing that makes or breaks this project

**Player-less headless materialization of a blueprint.** A placed blueprint is only
ghosts until a builder builds it; headless has no player. Phase 0 must prove a Lua
mod/scenario can `create_entity` a blueprint, feed it (`infinity-chest`/`infinity-pipe`),
warm it up, and read throughput via `force.get_item_production_statistics(surface)`
reproducibly to <1%. This is harder than reading the counter — do not under-scope it.
Everything downstream (the loop, the LLM) is trivial by comparison.

## Verified facts (do not re-derive from training data)

- **draftsman 3.3.0**: `Blueprint` lives in `draftsman.blueprintable`, NOT
  `draftsman.blueprint`. Decode with `get_blueprintable_from_string`. Round-trip
  (build → `to_string()` → decode) works and is the basis of the test fixtures.
- **Production stats API is per-surface since 2.0**: `force.get_item_production_statistics(surface)`
  (a method taking a surface), not the old `force.item_production_statistics`. Still
  to be confirmed against the official Factorio runtime docs before the Lua mod relies on it.
- Factorio **headless is free** (no DLC needed) but only knows Space Age entities if
  the DLC is installed. Phases 0–3 are designed for free vanilla 2.0.

## Conventions specific to this repo

- **Python ≥ 3.10**, src-layout, `pip install -e ".[dev]"` into `.venv/`.
- **TDD for real from the Lua materialization step onward.** The initial `blueprint.py`
  was scaffolded with its tests together (a foundation, not a red→green cycle) — say so
  honestly; do not claim TDD where it wasn't.
- `blueprints/` holds input/output blueprint strings (`.txt`). `mods/` will hold the
  Lua instrumentation mod. `docs/plans/` is gitignored (ephemeral), `docs/specs/` is not.
- The repo is **public** (or will be). Code, comments, commits, docs: English only.
  Conversation with Géraud: French.

## Not yet decided (open design choices — ask, don't assume)

- **Path A vs B** for measurement: `--benchmark` on a pre-warmed save (UPS) vs a scripted
  headless scenario (throughput in one run). Settle in Phase 0; B is the leaning.
- Lightweight self-written loop (à la Karpathy) vs plugging in **OpenEvolve**. Lightweight
  first to validate the evaluator, migrate once it's reliable.
- MOME storage: one elite per (cell × objective) is the adopted resolution to the
  "one elite per cell vs variable lead objective" contradiction; the git **semantic merge**
  rule is a component still to be written.

## Naming / external

- GitHub: `geriwald/factorio-forge` (name verified free; not yet pushed as of scaffold).
- Future domain `factorio-forge.com` (verified available, deliberately NOT registered yet).
- Community diffusion is a project objective; target creator = Nilaus. He **codified/
  democratized** the city block — he did not invent it. Getting this attribution wrong
  burns credibility. Do not contact him before a non-comparative "wow" artifact exists.
