# Phase 0 — Evaluator feasibility design

- **Date**: 2026-06-09
- **Status**: implemented and validated (AC1–AC4 met; see Implementation findings)
- **Design doc**: [`docs/design.md`](../design.md) — Phase 0 section (the "make-or-break" link)
- **Phase**: 0 (Workshop regime, the evaluator's real risk)

## Problem

The whole project hinges on one unproven capability: **materializing a blueprint
in a player-less headless Factorio and measuring its throughput reproducibly.**
A placed blueprint is only *ghosts* until a builder builds it; headless has no
player. We must prove a Lua scenario can `create_entity` a blueprint, feed it,
warm it up, and read throughput to <1% reproducibility. Everything downstream
(the loop, MAP-Elites, the LLM) is trivial by comparison and worthless if this
link is not proven.

## Decisions (validated 2026-06-09)

1. **Path B, not Path A.** A scripted headless scenario (`on_tick` loop) that
   materializes, feeds, warms up, and measures throughput in a single run —
   *not* `--benchmark` on a pre-warmed save. Path B gives throughput directly and
   is simpler to close for Phase 0. Path A (UPS via `--benchmark`) is deferred.
2. **Scenario, not mod.** Materialization lives in a self-contained scenario
   (`control.lua`), launched headless. It does not touch the player's installed
   mods or saves in `~/.factorio`.
3. **TDD applies to the Python harness, not the Lua.** The Lua runs inside the
   Factorio runtime, not pytest. The red→green cycle is on the harness: a Python
   test that launches the scenario on the toy blueprint and asserts a `float`
   plates/s is returned — red while the scenario does not exist, green when it works.

## Verified facts (read from official runtime docs, 2026-06-09)

- Binary: `~/Games/factorio/bin/x64/factorio`, version **2.0.76** (build 84451,
  linux64, full, space-age). Standalone (not Steam). Responds to CLI headless
  (`--version` confirmed). Phase 0 stays on **vanilla 2.0** (no Space Age entities).
- `force.get_item_production_statistics(surface)` → `LuaFlowStatistics`. The
  `(surface)` argument is correct (per-surface since 2.0). Confirmed against
  `lua-api.factorio.com/latest/classes/LuaForce.html`. **However, see the
  implementation finding below: this stat did NOT register furnace production in
  our scenario, so it is not the measurement we use.**
- Decode the blueprint at runtime via a script `LuaItemStack`: `import_stack(str)`
  (returns 0/-1/1) then `get_blueprint_entities()`. Materialize with
  `surface.create_entity{...}`. Confirmed against the runtime docs and in practice.

## Measurement protocol

**What we measure is CONVEYED throughput, not raw machine production.** A design's
efficiency is what actually reaches the output, not what the machines theoretically
craft — measuring per-machine production would bias the evaluator optimistically
(the surrogate-exploitation pitfall) and ignore conveyance losses. Conveyance also
ties into UPS: a saturated belt / full output is both higher-throughput and cheaper
for the engine to simulate. So throughput is read at the **output (sink) chest**.

1. **Materialize** — decode the blueprint, `create_entity` each entity (position,
   direction, recipe for assembling machines; furnaces auto-select their recipe).
2. **Feed** — the first `infinity-chest` supplies the input item infinitely; an
   `electric-energy-interface` supplies power. **The blueprint carries its own
   electrical network (poles): power routing is part of the design, not faked by
   the scenario.** The last `infinity-chest` is a passive sink we measure.
3. **Warm up** — run `WARMUP_TICKS` to reach steady state.
4. **Measure** — record the sink chest's count of the target item at `T0`, run
   `MEASURE_TICKS`, record at `T1`. `rate = (count_T1 - count_T0) / (MEASURE_TICKS/60)`.
   Raw machine production (`products_finished` summed over crafters) is recorded as
   a **secondary** figure, enabling a conveyance-yield (conveyed / produced) metric.
5. **Emit** — write the figures to `script-output/phase0-result.json` (parsed by
   the harness, which returns the conveyed rate as a Python `float`).

The harness runs the binary headless, on a given blueprint, and returns the float.

## Implementation findings (2026-06-09)

Discovered while making Phase 0 work; recorded because they were non-obvious and
contradict assumptions in the original plan:

- **Player-less tick advance.** `--start-server-load-scenario` runs a windowless
  server, but it pauses ticks with no player connected. Two things were needed:
  `auto_pause: false` in a generated `server-settings.json`, **and keeping the
  process's stdin open** (an EOF on stdin leaves the server not advancing ticks).
- **Production stats API did not register furnace output.** With furnace and stats
  read on the same force+surface (`player`/`nauvis`), `output_counts["iron-plate"]`
  stayed `nil` while the furnace's own `products_finished` counted correctly. So we
  measure at the sink chest (and this is the right grandeur anyway — conveyed, not
  produced).
- **Inserter `direction` is the PICKUP side**, not the drop side. A west->east flow
  needs `direction = West (12)`.
- **`game.speed`** is raised (CPU-bound) so a long, statistically-clean window
  (18000 ticks) runs in seconds of wall time instead of minutes. Per-tick
  throughput is unchanged.
- **Result**: AC2 reproducibility is not merely <1% but **exactly 0%** across runs
  (Factorio's determinism at constant version+scenario+blueprint).

## Toy case

A small iron-plate smelting array: infinite iron ore in (`infinity-chest`),
electric furnaces, iron plates out. Smallest case that exercises the full chain
(materialize → feed → warm up → measure). Vanilla 2.0, no Space Age.

## Acceptance criteria

- **AC1** — From a fixed input blueprint string, the harness returns a conveyed
  iron-plates/second `float`. (Materialization works — not just stats reading.)
- **AC2** — The figure is **reproducible to <1%** across repeated runs at constant
  (version + scenario + blueprint). This is *the* Phase 0 success criterion.
  **Met: observed spread is 0.0%.**
- **AC3** — The harness runs fully headless (no X server, no player), invocable
  from a Python test, suitable for later automation in the loop.
- **AC4** — Nothing writes to the player's `~/.factorio` mods or saves; the
  scenario and any state are isolated under the project (dedicated config /
  mod-directory / script-output as needed).

## Scope

- Lua scenario: materialize + feed + warm up + measure, for the toy smelting case.
- Python harness: launch headless, run scenario, parse figure, return `float`.
- Python test (red first): assert the harness returns a plates/s `float` for the
  toy blueprint; a reproducibility assertion for AC2.
- A committed toy blueprint string fixture under `blueprints/`.

## Out of scope (Phase 0)

- Path A `--benchmark` / UPS measurement.
- Any MAP-Elites, archive, mutation loop, or LLM in the loop (Phases 1+).
- Space Age entities (foundry, recycler, …) — vanilla 2.0 only.
- Generalizing beyond the toy smelting case (arbitrary recipes, fluids beyond
  what the toy needs, multi-surface). Proven on one case first.
- EULA automated-use clause review — flagged in the design doc as a pitfall;
  not blocking for a single-instance local prototype, revisit before scaling.

## Open questions to settle during implementation

- **Launch mechanism**: `--load-scenario <name>` (needs the scenario discoverable
  in a scenarios dir) vs packaging as a one-shot map gen. Settle by reading how
  2.0 resolves scenario paths headless; isolate via `--config` / `--mod-directory`.
- **Output channel**: a parseable stdout log line (`script.log` / `log()`) vs a
  file written via `helpers.write_file` to script-output. Pick the most
  deterministic to parse.
- **WARMUP_TICKS / MEASURE_TICKS**: tune empirically until AC2 (<1%) holds.
- **infinity-chest feed rate**: high enough that the furnaces are never the
  bottleneck's victim of starvation (we want the *factory* to be the limiter).
