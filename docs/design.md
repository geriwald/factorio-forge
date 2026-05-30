---
title: "Factorio as a testbed for emergent optimization with Claude Code"
type: research
created: 2026-05-30
modified: 2026-05-30
status: draft
confidence: medium
tags: [factorio, autoresearch, evolutionary-search, quality-diversity, map-elites, speedrun, claude-code, recherche-emergente]
aliases: ["Projet Factorio autoresearch", "Factorio AlphaEvolve", "Optimisation émergente Factorio", "Workshop Workbench Campaign Factorio"]
---

# Factorio as a testbed for emergent optimization with Claude Code

Personal research project (with Luidjib, collaborative by intent): use an LLM-driven optimization loop — modeled on Karpathy's *autoresearch* and the FunSearch → AlphaEvolve lineage — to make Factorio production structures emerge that are **not** the canonical designs copied everywhere. Working hypothesis: optimizing a chosen objective under explicit diversity pressure (Quality-Diversity / MAP-Elites) yields an archipelago of high-performing, unexpected solutions rather than a single optimum that collapses back onto established community knowledge.

The project is organized around **three nested optimization regimes** (artisanal naming: **Workshop → Workbench → Campaign**), linked by a **Catalog** of characterized blocks, all deposited in a **git-versioned multi-objective elite archive** that simultaneously serves as the diversity engine, the stepping-stone mechanism, and the collaborative substrate. The evaluation objective is **agnostic**: any objective (throughput/SPM, compactness, aesthetics, robustness, human portability, or **speedrun/TAS time**) can be promoted to the lead objective per session, while the others are measured *for information* when cost allows. A cross-cutting, non-technical but structuring objective is **community diffusion**: produce a Wow-effect demonstrator able to attract influential creators (Nilaus as the first target) to bootstrap the collaborative dynamic.

This document lays out the framing, architecture, objectives, diffusion strategy, pitfalls, and an incremental experiment plan. It does not claim that "real" emergent structures (in the strong, artificial-life sense) will appear — hence the "not really, but the equivalent" of the initial request: this is emergence in the weak, engineering sense, of solutions not anticipated by the designers.

## The problem, stated honestly

Factorio is a logistics-chain optimization game where, over ten years, the community has converged on a corpus of **canonical designs**: production ratios ("1 oil refinery to 5 chemical plants to 7 plastic assemblers"), architectures (main bus, city blocks, bus-less early-game spaghetti), and copied beacon books. These designs are near-optimal for the obvious metrics (items/second, compactness). The point is not to reproduce them — an experienced player or a wiki already does that — but to see whether automated search **finds something else**: unexplored trade-offs, geometries nobody tried because they're counter-intuitive, optima on metrics the community ignores (failure robustness, energy density, startup latency).

The central risk, to name up front: **a single-objective optimizer almost always converges to the canonical**, because the canonical *is* the optimum for the obvious metric. To get the unexpected, you must either change the metric or — the bet of this project — add explicit diversity pressure.

## Available building blocks (real state of the art, May 2026)

### 1. Autoresearch (Karpathy) — the loop pattern

[`karpathy/autoresearch`](https://github.com/karpathy/autoresearch) (released 7 March 2026, tens of thousands of stars) is an LLM agent that runs ML experiments autonomously: it edits `train.py`, launches a fixed-duration training run (~5 min), evaluates against a validation metric (`val_bpb`), **keeps the winning change, discards the losers (accept/reject mechanism), and repeats**. High-level instructions live in a `program.md`. Per Fortune, Karpathy reports that applying the ~20 discovered tweaks to a larger model gave a ~11% training speedup (figure not confirmed by the primary repository).

What transfers to Factorio: the *propose → evaluate within a time budget → keep if better → iterate* loop. What does not transfer as-is: autoresearch edits Python training code; we will edit **blueprint descriptions** (or the Python code that generates them). The `val_bpb` metric becomes an **in-game measured throughput**.

### 2. FunSearch → AlphaEvolve — the scientific lineage

The serious theoretical lineage is not autoresearch (an elegant hack) but **FunSearch** (DeepMind, 2023) and its successor **AlphaEvolve** (DeepMind, 2025, arXiv 2506.13131). Principle: couple an LLM (proposing code mutations) with an **automatic evaluator** (scoring) in an evolutionary loop. FunSearch solved open math problems (cap set); AlphaEvolve improved matrix multiplication (4×4 complex in 48 multiplications, beating Strassen 1969) and optimized real Google infrastructure. Key difference: FunSearch evolved a single function, AlphaEvolve evolves whole codebases and does **multi-objective**.

Directly usable open-source implementation: [`openevolve`](https://github.com/algorithmicsuperintelligence/openevolve) (`pip install openevolve`). Relevant architecture for us:
- **Weighted LLM ensemble** (OpenAI-compatible models) for explore/exploit — pluggable onto Claude via a compatible API.
- **Cascade evaluator**: stage 1 = fast checks (code imports/executes), stage 2 = light tests, stage 3 = full benchmark, with thresholds that cull weak candidates early. **This is exactly the pattern we need**: stage 1 = the blueprint is syntactically valid; stage 2 = it builds in-game without collision; stage 3 = measure throughput over N ticks.
- **MAP-Elites archive with configurable feature dimensions** + an **island-based** model (ring topology, controlled migration) that prevents premature convergence — and which, as it happens, gives us a natural substrate for the multi-objective / multi-contributor case (see archive section).
- **Artifact side-channel**: error traces flow back into the next prompt (the agent learns from its failures).

### 3. MAP-Elites / Quality-Diversity — the key to emergence

This is the block that directly answers the "something other than canonical" objective. **MAP-Elites** (Multi-dimensional Archive of Phenotypic Elites) does not optimize *one* optimum: it **illuminates the search space**. You define behavior dimensions (e.g. "floor area" × "number of beacons" × "buffering ratio"), discretize into cells, and keep the best solution **per cell**. The result is not a design but a **map**: "here's the best compact-no-beacon design", "here's the best sprawling-overclocked design", etc.

Why it produces the unexpected: by forcing cells nobody normally optimizes to be filled (the "large area but zero beacons" corner, or "average throughput but ultra-robust"), you discover viable designs in regions the community ignored because they don't maximize the obvious metric. QD has already produced surprising results in evolutionary robotics and design — **but nobody has published it on Factorio**. That is the project's original angle.

### 4. factorio-draftsman — blueprint manipulation

[`factorio-draftsman`](https://github.com/redruin1/factorio-draftsman) (v3.3.0, Python ≥ 3.10): decodes/encodes blueprint strings (base64 + zlib + JSON), validates spatially (collisions, connections), builds programmatically. Supports Factorio ≥ 1.0 and **2.0** (confirmed). For **Space Age** entities (foundry, recycler, big mining drill…), support is *inferred*: you would update the prototype database by pointing at a Factorio installation (the exact CLI — `draftsman factorio-version latest` vs `draftsman-update -p <folder>` — has changed across versions, to be verified for v3.3.0). **The game binary is not required to generate/analyze** — only to visualize and benchmark.

### 5. Factorio headless — the deterministic evaluator

This is the block that closes the loop. Factorio headless (Linux, free, no UI) can benchmark a savegame **deterministically and reproducibly**:

```
./factorio --benchmark "save.zip" --benchmark-ticks 1000 --disable-audio
```

Results vary by less than 0.1% between runs (source: mulark test bench). Convert `avg_ms` to UPS via `1000 / avg_ms`.

**Caution — two distinct measurements not to confuse:**
- `--benchmark` measures **simulation speed** (UPS, CPU cost/tick) by **replaying a frozen savegame** for N ticks. It does not "start" a fresh factory: all warmup must already be done in the save.
- **Production throughput** (items/second) is read via Factorio's statistics API: `force.get_item_production_statistics(surface)`, which returns a `LuaFlowStatistics` (`output_counts`, `get_flow_count{…}`). Since 2.0, **production is per surface** (Nauvis, Vulcanus, space platforms): instrumentation must specify the surface — trivial single-surface (Phases 0-3), to be clarified in Space Age multi-planet (Phase 5).

These two measurements do not combine within a single `--benchmark` (benchmark mode restricts script execution). **Two possible paths**, to be settled early:
- **Path A** — `--benchmark` for UPS on a **pre-warmed** save, throughput read separately.
- **Path B** — a **scripted headless scenario** (`on_tick` loop) that materializes, feeds, warms up, and measures throughput in a single run, without `--benchmark`. More flexible for throughput; probably the right one for this project.

This is the main integration work — and it's heavier than "read a counter" (see next section).

**Important caveat (verify experimentally):** headless is free, but **it only knows Space Age entities if the DLC is present in its installation**. Without the DLC, you're limited to vanilla 2.0. The DLC is paid. To decide: do Phase 1 in vanilla 2.0 (free, sufficient to validate the whole chain) before investing in Space Age.

## From blueprint to benchmarkable savegame — the real critical link

This is the most underestimated difficulty, harder than reading statistics. **A blueprint string is not a running factory, and `--benchmark` takes a savegame, not a blueprint.** Between the two, three non-trivial steps, all in **headless, therefore without a player**:

1. **Materialize the blueprint.** A placed blueprint is just a set of *ghosts* until builders (a player, or logistic robots + roboport + powered electric network) build it. In headless, **there is no player**. So you need a mod/scenario in Lua that parses the blueprint and calls `surface.create_entity{…}` for each entity (position, direction, recipe, modules), bypassing ghosts. **This is a mini headless construction engine, not a counter reader.**
2. **Feed the inputs.** A factory with no inputs produces zero. You must inject input resources at guaranteed rate: `infinity-chest` / `infinity-pipe` (native 2.0 editor entities) placed upstream, or per-tick Lua insertion. To be integrated either into the generated blueprint or into the harness.
3. **Warm up then measure.** Let it run for X ticks to reach steady state (buffers full, robots deployed), *then* read throughput over Y ticks. And, if you also want UPS via `--benchmark`, save the pre-warmed state as a savegame.

**Effort implication**: the "lightweight variant" below is not ~200 lines — the Lua component for materialization + feeding + warmup + measurement is the heart of the project. The cascade evaluator earns its keep here: kill 90% of candidates at **stage 1** (draftsman validation, instantaneous) before paying for a materialization + simulation.

## The dynamic dimension: three nested regimes

Factorio is not only a spatial problem ("what is the best factory?"), it is a **temporal** one: you don't build a megabase without an initial base, you don't do endgame quality-max without efficient interplanetary logistics. There are **tiers to clear**, technological prerequisites, resource accumulation. Optimizing a frozen blueprint (infinite resources, steady state) and optimizing a progression from zero to endgame are **two problems of different nature**. We distinguish three regimes, simplest to hardest (artisanal naming):

| Regime | Name | What is optimized | I/O resources | "Time" | Eval difficulty |
|--------|------|-------------------|---------------|--------|-----------------|
| **1** | **Workshop** | An isolated functional block, at steady state | Idealized (infinity-chest) | Absent — steady state | Low (≈ Phase 0) |
| **2** | **Workbench** | The best *achievable* block given unlocked tech / quality | Finite per tier | Discrete — tech tiers | Medium |
| **3** | **Campaign** | The temporal sequence of blocks, from zero to a target state | Finite, accumulating | Continuous — minimize total time | Very high |

The natural objection to the Campaign regime — "simulating a full game per candidate costs hours" — is resolved by **hierarchical decomposition with a surrogate model**, which is the project's structuring idea:

### The Catalog: interface between Workshop and Campaign

The **Campaign regime does not simulate Factorio**. It reasons over a **macro model** where each block is a characterized **contract**: "block *green-circuit-mk2* consumes N iron/s + M copper/s, produces P circuits/s, occupies S tiles, requires tech T, costs C resources to build." These numbers come from the **Workshop** regime (measured in headless, idealized I/O). The set of these contracts forms the **Catalog** (*Atlas*): a library of blocks indexed by their capabilities. The Campaign does not see blueprints, it sees **Catalog entries with numbers on them**.

The macro state at an instant = a vector (unlocked techs, reachable quality, accessible planets, stocks). A decision = build a block / launch a research / send a rocket. The objective = reach a target state minimizing time (or resources). This is formally a **planning graph** or a **mixed-integer linear program spread over time** — solvable in milliseconds by an OR solver *or* explored by an LLM-evolutionary loop proposing decision sequences. **This is where emergence becomes strategic** (counter-intuitive unlock orders, throwaway transitional blocks) — and it is probably more fertile than spatial emergence, because human players optimize their progression with coarse heuristics, never globally.

**Surrogate pitfalls (to own as research questions, not flaws):**
1. **The macro model is optimistically biased — and worse, adversarially so.** A block measured in isolation with idealized I/O performs better than wired into a real, imperfect logistic chain (belt saturation, robot latency, electrical contention). The danger is not the *magnitude* of the error but its *structure*: the trajectory optimizer will **actively exploit the regions where the surrogate is most optimistic** (the classic model-based-optimization / Goodhart failure mode). The error on the *selected* trajectory is therefore systematically worse than the model's average error. Countermeasure required by design: trust region, out-of-distribution novelty penalty, or re-verifying the top-k trajectories in real simulation *before* trusting them — not just the final one.
2. **Composition is non-linear and discontinuous.** Two blocks viable in isolation can deadlock together (bus contention, undersized power network, robot latency breaking an assumed steady-state throughput). A deadlock is not "10% less", it is **zero** — a discontinuity an additive surrogate structurally cannot represent.
3. **The Catalog is expensive to fill** (each entry = a Workshop campaign). Trade-off: how many blocks to characterize before planning becomes possible?
4. **Verification is mandatory.** At some point, close the loop: actually play a trajectory the Campaign judges optimal and measure the prediction-vs-reality gap. Otherwise you optimize a fiction.

The nesting means **nothing is wasted**: the Workshop regime (Phase 0, feasible right now) directly produces the Campaign's building blocks. So we can start with the Workshop while keeping the Campaign on the horizon.

## The central object: a multi-objective elite archive

The core of the apparatus is **neither a blueprint nor a trajectory**: it is the **archive**. A table where each entry is an elite (a Workshop structure, or a Campaign trajectory) together with:
- the **structure** (blueprint string, or decision sequence);
- a **primary score** — the *active* eval objective, the one selection runs on;
- a **vector of secondary scores** — all other objectives, measured *for information* when cost allows;
- **behavior coordinates** — the dimensions that partition the archive into MAP-Elites cells.

Operating mode, **hybrid and objective-agnostic** (validated design choice):
1. **Select a lead objective** for the session (any of the objectives below can be promoted).
2. **Pick a starting elite** from the archive — including an *intermediate* deposited by a prior run under a *different* objective, or by another contributor. This is **stepping-stone** exploitation: the best final solutions often pass through states non-optimal for the final objective.
3. **Mutate** (Claude proposes a variation) → **evaluate** (primary + all affordable secondaries) → **place** into its cell if the elite beats the occupant on the active objective.

Thus "restart from an intermediate under a different objective" becomes a **first-class operation**: change the primary objective, point the loop at a region of the archive, relaunch — and accumulated elites serve as stepping stones for the new objective.

### Resolving the multi-objective ⇄ "one elite per cell" contradiction

Naively, "one elite per cell" and "variable lead objective" contradict each other: if "best" is only defined relative to the current lead objective, a session on objective B could **overwrite** an elite that was optimal under objective A — destroying reusable capital and breaking the stepping-stone promise. This must be resolved explicitly. Adopted design: **MOME (Multi-Objective MAP-Elites)** — the cell key includes the objective, i.e. one elite per **(cell × objective)**. This costs storage proportional to the number of objectives but keeps each objective's best per region intact and reusable as a stepping stone. (Alternative considered: a Pareto front per cell — richer, but "one elite per cell" falls and git merges become Pareto-front merges. OpenEvolve's island model maps naturally onto this: one island per contributor/objective, with controlled migration.)

### The collaborative angle — and its merge pitfall

The collaborative angle follows directly from a **git archive** (consistent with the Gitflow discipline, TDC13): each elite is a file (structure + scores + metadata); multiple contributors' archives **merge**; an elite found by one under "max throughput" becomes the starting point for another's "portability" optimization; the git history *is* the research journal. This is Karpathy's autoresearch (keep winners on git) **extended to multi-objective and multi-contributor**.

**Merge pitfall (must be named):** a naive git merge (file-per-elite, last-writer-wins / textual conflict) does **not** know that two contributors who touched the same cell under different objectives hold two legitimate optima. A **semantic merge rule** is required (replay the domination/MOME rule, not a text merge) — otherwise "the git history is the research journal" becomes "the git history corrupts the archive." This is a component to be written, not a free property.

**Cost-asymmetry pitfall:** scores do not all cost the same. Compactness and regularity read off geometry (free, instant, draftsman); SPM, robustness, speedrun time require a (costly) simulation. Measuring *all* objectives for information on every candidate would blow up cost. Mitigation: the **cascade evaluator** — free geometric objectives at stage 1 (all candidates), costly simulated objectives at stage 3 (survivors only). The archive must therefore accept **partial score vectors** and allow "completing" an elite's evaluation on demand. Sub-pitfall: you cannot dominate on an objective whose score has not yet been computed for the occupant — so the comparison semantics for "occupant has NULL on the new objective" must be specified (complete it before comparing, rather than comparing against unmeasured values).

## Objective ideation

The optimization objective is not given: it is itself a design space. We distinguish **intrinsic** objectives (measured on the structure) from **extrinsic** ones (measured against a human reference). The speedrun flips the project from "exploration with no judge" to "there's a record, beat it."

| Family | Objective | Metric | Automatic judge | Eval feasibility |
|--------|-----------|--------|-----------------|------------------|
| **Throughput** | Production | **SPM** (science/min), items/s | production stats (Workshop) | ✅ acquired (Phase 0) |
| **System efficiency** | Flow saturation | % of full lanes, throughput/entity, items·s⁻¹·W⁻¹ | measurable in-game | ✅ medium |
| **Compactness** | Density | throughput/tile, total area | geometry (draftsman) | ✅ easy |
| **Aesthetics** | Regularity, alignment | symmetry, periodicity (autocorrelation), placement entropy | **computable on geometry** | ⚠️ to define |
| **Human portability** | Modularity | tileability, city-block conformance, beacon-book reusability | structural heuristics | ⚠️ subjective |
| **Pedagogy** | Books per phase | coherent start → mid → endgame progression | judgment (human + LLM) | ⚠️ qualitative |
| **Speed (extrinsic)** | **Speedrun / TAS** | **time to objective** | **game timer + leaderboard** | ✅ unambiguous, ❗ costly |
| **Robustness** | Failure tolerance | residual throughput after destroying k% of entities | perturbed simulation | ⚠️ medium |

Cross-cutting variants: **with or without the Space Age DLC**; **per game phase** (start / mid / endgame). Three substantive remarks:

- **Aesthetics is measurable**, and it's an underexplored angle. "Regularity" and "alignment" formalize (spatial periodicity, fraction of grid-aligned entities, direction entropy). Open question: *is an aesthetically regular design also performant, or is there a beauty/throughput trade-off?* — perfect as a MAP-Elites dimension.
- **Human portability is in direct tension with pure optimization.** A machine-optimal design is often unreadable (dense spaghetti); a portable design (city block, reusable beacon book) sacrifices some performance for reusability. **Optimizing portability means optimizing for humans — probably the most concretely useful deliverable**, and the terrain that speaks to creators like Nilaus.
- **Speedrun/TAS has the most solid judge**: unambiguous metric (time), defined target state, *and a public human record to beat*. Research finding: the Factorio speedrun community **already does TAS** (Tool-Assisted Speedrun) — the [`AnyPctTAS`](https://mods.factorio.com/mod/AnyPctTAS) mod exists, and official leaderboards exist for both vanilla and Space Age. **However, the bounds are not interchangeable and must be dated:**
  - Human Any% solo ~1h27 (Nefrums, vanilla 1.x; the solo record has oscillated around 1h21–1h27).
  - Human Any% multiplayer ~1h15 (Team Steelaxe, FFF#344, vanilla).
  - TAS WR **1h21:20 (Gotyoke, 2020, Factorio 0.18, vanilla pre-Space-Age)** — *not* a current bound: it predates 1.0/2.0, whose mechanics and ratios differ, so it is not directly comparable to current play.
  - **There is no Space Age TAS.** This is an *argument for* the project (virgin territory), not against: "converging toward the TAS format" in Space Age would mean producing **the first** Space Age TAS, not beating an existing record.

## Diffusion strategy and Wow demonstrator

Without a community, the collaborative archive stays a solitary exercise. **Diffusion is therefore a project objective**, not an afterthought. First target: **Nilaus** (Christian Nilaus), creator of the *Factorio Master Class* — the human embodiment of what the machine attempts (take an objective, invent an optimized method the community adopts).

**Exact attribution (critical for credibility)**: Nilaus did **not** invent the city block — he **codified and democratized** it via his Master Class and blueprint books (City Block 100×100, Solar Block, grid-aligned rail segments), to the point of making it the de facto standard. The safe framing — which does not depend on proving any prior art (which we have not sourced) — is: "you turned it into a teachable, standardized method." The merit "scattered idea → method" holds even if the scattered idea isn't documentable, and it is both true and flattering (turning an idea into a teachable method is rarer than having the idea). Telling him "you invented the city block" would discredit us in the first sentence. His current project — *True Megabase* aiming for 1M+ SPM in Space Age, with space platforms, asteroid collectors, quality upcycling (confirmed via Patreon + YouTube) — confirms the initial intuition and makes him a natural target for the "portability" and "Space Age" objectives.

**To deepen before any contact**: the technical detail of his recent Space Age innovations (ships in asteroid fields) is not verified by reading — sources to mine: his Patreon, FactorioPrints, his Nilaus.TV Confluence. We do not approach him without studying his builds closely.

**Pitch angle** (honest, positions him as judge-consultant, not experimental subject):
> "You've spent years hand-inventing optimized production methods. The question: **can an automated optimization loop discover methods you wouldn't have found?** Not to replace you — to give you a *stepping-stone generator*. You set an objective (a more compact beacon book, a more efficient asteroid ship), it illuminates the design space and brings you unexpected candidates to refine."

**Mandatory sequencing**: do **not** contact Nilaus before having an artifact that lands. But note the terrain tension: Phases 0-2 run on **vanilla 2.0 single-surface** (smelting, green circuits) — exactly the most *saturated*, most hyper-optimized canonical terrain, where beating the human is hardest. A frontal "more compact than Nilaus's standard" there is a competition lost in advance. So the Wow target should be **non-comparative**: not "better than his standard" but "a viable design in a MAP-Elites cell nobody optimizes" (robustness, aesthetics) — a "huh, I wouldn't have thought of that" rather than a "that beats mine." Approaching a creator of this caliber with a slide deck and no demo burns the cartridge. Sequence: demonstrator first (through Phase 2-bis on a terrain of his domain), approach next, integration as consultant if it sticks. Secondary targets (other high-audience creators) to map once the demonstrator is proven.

## Proposed architecture

The full loop, assembling the blocks above:

```
┌─────────────────────────────────────────────────────────────────┐
│                    OPTIMIZATION LOOP                              │
│                                                                   │
│  ┌──────────┐   propose mutation   ┌─────────────────────────┐   │
│  │  Claude  │ ───────────────────► │  Blueprint generator     │   │
│  │ (LLM)    │                      │  (Python + draftsman)    │   │
│  └────┬─────┘                      └───────────┬─────────────┘    │
│       │                                        │ blueprint string │
│       │ artifacts (errors,                     ▼                  │
│       │ scores, traces)            ┌─────────────────────────┐    │
│       │                            │  Cascade evaluator       │    │
│       │                            │  S1: valid (draftsman)   │    │
│       │                            │  S2: builds (Lua)        │    │
│       │                            │  S3: headless benchmark  │    │
│       │                            │      → throughput, watts │    │
│       │                            └───────────┬─────────────┘    │
│       │           score + behavior             │                  │
│       │                                        ▼                  │
│       │                            ┌─────────────────────────┐    │
│       └────────────────────────────│  MOME elite archive      │   │
│                                     │  (cells × objective,     │   │
│                                     │   git-versioned)         │   │
│                                     └─────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

Two implementation variants, simplest to most ambitious:

**Lightweight variant (recommended to start)** — skip OpenEvolve, write the loop ourselves à la Karpathy: Claude Code edits a `generate_blueprint.py` script, a harness runs the headless benchmark, keeps the winner on a git branch, logs the score. We control everything and learn the Factorio pitfalls before industrializing. Direct application of the autoresearch pattern.

**Heavyweight variant** — plug in OpenEvolve: provide the cascade evaluator (calling draftsman + headless), configure the LLM ensemble on Claude, enable QD mode (OpenEvolve natively includes a MAP-Elites archive with islands). More powerful, but you inherit OpenEvolve's complexity before validating that the Factorio evaluator works.

**Recommended decision:** lightweight variant first (validate the evaluator, the real risk), migrate to OpenEvolve once the evaluation chain is reliable.

## What makes this project hard (the pitfalls)

Listed explicitly because they determine whether the project succeeds or stalls:

1. **The evaluator is everything — and its hardest part is materialization, not measurement.** Without reliable automatic evaluation there is no autoresearch — just an LLM generating at random. 80% of the effort is in the "blueprint string → **factory materialized and fed without a player** → throughput measured" chain. The genuinely risky link is the first (materializing a blueprint headless, cf. dedicated section), not the last.
2. **Measuring throughput ≠ measuring UPS.** Native `--benchmark` measures *simulation speed* (UPS) replaying a frozen save, not *production*. Throughput is read via `get_item_production_statistics(surface)`. The two don't combine in one `--benchmark` — hence the Path A / Path B choice above.
3. **Warmup and ramp-up.** A factory takes time to reach steady state (buffers filling, robots deploying). Benchmarking too early measures the transient. Protocol needed: inject inputs at infinite rate, run X ticks, *then* measure over Y ticks.
4. **The design space is gigantic and most mutations are invalid** (collisions, disconnected entities, absurd recipes). The LLM must generate *plausible* blueprints, not noise. Hence generating via structured Python code (draftsman validates collisions) rather than emitting raw JSON.
5. **The "non-canonical" may just be "bad."** Distinguish a real discovery from a merely sub-optimal design the community discarded for good reasons. The QD metric must capture a *genuinely interesting* dimension (robustness, modularity), else you illuminate void.
6. **Two first-order costs**, not just tokens: (1) **machine time** — each eval = materialize + warm up + N ticks, possibly minutes × thousands of candidates (this is why Karpathy capped runs at 5 min, and what the cascade evaluator mitigates); (2) LLM API cost. Cheap model (Haiku) for mass generation, Claude Opus for reflection/analysis.
7. **Determinism guaranteed only at (version + mods + platform) constant.** As soon as the instrumentation mod runs, you're in a modded game: freeze the mod version in the experiment hash, else runs aren't comparable over time.

## Incremental experiment plan

Designed so each phase yields an exploitable result and de-risks the next. Consistent with Géraud's TDD/spec discipline — each phase has a measurable success criterion.

**Phase 0 — Evaluator feasibility (the real test, the real risk).** Goal: prove the whole "blueprint → measurement" chain, whose hardest link is **player-less headless materialization**. Decomposed: (a) a Lua mod/scenario materializes a blueprint via `create_entity`; (b) feed it (`infinity-chest`/`infinity-pipe`); (c) warm it X ticks; (d) read throughput via `get_item_production_statistics(surface)`. Toy case: an iron-plate smelting array (infinite ore in, plates/s out). Settle Path A vs B here. Vanilla 2.0, free. **Criterion: obtain an iron-plates/second figure reproducible to <1% from an input blueprint string — materialization, not just reading, must work.**

**Phase 1 — Naive single-objective loop (autoresearch pattern).** Claude edits a generator, the harness benchmarks, keeps the best. Metric: plates/s. **Hypothesis to test (not criterion): does the loop converge to the canonical, or diverge from it?** Community blueprints optimize an implicit mix (throughput *and* compactness *and* tileability *and* UPS-friendliness); a pure "plates/s" optimizer might diverge from the canonical rather than rediscover it — an interesting observation, not a failure. **Criterion: the loop converges to *a* stable, reproducible optimum** (whether it's the canonical is an observation to analyze).

**Phase 2 — MAP-Elites, first illumination + archive.** Add 2 behavior dimensions (e.g. floor area × number of beacons), illuminate, and set up the **git-versioned MOME archive** (free secondary scores measured on all candidates). **Expected result: a map of designs, some in cells the community doesn't optimize.** This is where we see whether "something else" emerges. **Criterion: at least one viable design in a non-canonical cell that we wouldn't have designed by hand.**

**Phase 2-bis — Wow demonstrator (diffusion milestone).** As soon as a presentable non-canonical result exists, push it onto a target creator's terrain: produce an artifact that would surprise Nilaus — but **non-comparative** (a robust/aesthetic design in an unoptimized cell), not "beats his standard" on the saturated vanilla terrain. **Criterion: a design an expert would recognize as "huh, I wouldn't have thought of that."** This is the entry condition for any community approach — not before.

**Phase 3 — Exotic metrics.** Switch the lead objective to things the community ignores: robustness (residual throughput after destroying k%), energy density (items·s⁻¹·W⁻¹), startup latency, or **measurable aesthetics** (regularity, alignment). **This is where the real-discovery potential is highest**, the optimum there being likely *different* from the canonical. This is also where **stepping stones** pay off: restart from a Phase 2 elite under a new objective.

**Phase 4 — From Workshop to Campaign (surrogate + planning).** Build the **Catalog** from characterized Workshop blocks, then the macro progression-planning model (Campaign regime) on a restricted tech sub-tree. **Decisive criterion: actually play a trajectory judged optimal and measure the macro-prediction-vs-reality gap** (the central research question). Natural objective: minimize time to a given state — i.e. **converge toward the speedrun/TAS format**, with the human bound where one exists.

**Phase 5 (optional) — Space Age.** If prior phases are conclusive, invest in the DLC and replay with Space Age entities (foundry, recycler, space platforms, quality — which radically change ratios and prerequisite-chain depth). The newer the game, the less frozen the canonical designs → more chance of finding the new, and the direct terrain of Nilaus's current work. Note: producing the *first* Space Age TAS lives here.

## Claude Code's role in the apparatus

Concretely, how Géraud (and Luidjib) use Claude Code here:

- **Building the chain**: Claude Code writes the draftsman generator, the Lua instrumentation/materialization mod, the benchmark harness, the OpenEvolve integration. Classic dev, TDD.
- **The agent in the loop**: for the lightweight variant, Claude *is* the mutation engine — it reads the previous run's score, proposes a generator change, we benchmark. Literally Karpathy's `program.md`, driven interactively or in an automated loop (`/loop`).
- **Analyzing results**: once the MAP-Elites archive is filled, Claude analyzes the emergent designs, explains *why* a given non-canonical design works, and makes it legible (the meaning, not just the number).
- **The research journal**: each experiment documented in `research/thesis/` or a dedicated subfolder, with sources and results — exactly this vault's discipline.

## Limits

- **"Emergence" is claimed in the weak sense.** Solutions not anticipated by the human optimizer, not strong emergence in the artificial-life or self-organized-complexity sense. The title and ambition must stay honest about this. (Cf. the initial request: "not really, but the equivalent.")
- **Discovered novelty is bounded by the human choice of behavior descriptors.** MAP-Elites illuminates the space *it is told about*, not the space itself. Choosing "area × beacons" will mostly (re)discover the compactness/overclock trade-off the community already knows. The "unexpected" is therefore largely pre-determined by the designer of the axes — the project's most serious conceptual limit.
- **The make-or-break link is player-less headless materialization of a blueprint**, not statistics reading. Plausible (the `create_entity` API exists) but **not verified by reading code** in this note — first Phase 0 prototype.
- **`get_item_production_statistics(surface)` not verified against the Factorio runtime docs** at time of writing (corrected from an earlier erroneous `item_production_statistics`) — signature and per-surface semantics to confirm by reading the official API docs.
- **No known publication of MAP-Elites on Factorio** — original angle, but no proof it works on this domain. Assumed risk.
- **Surrogate adversarial exploitation** (Campaign regime): the macro model isn't just imprecise, it's gamed by the optimizer (Goodhart) and blind to compositional discontinuities (deadlocks). Requires a design countermeasure (trust region / top-k re-verification), not just a posteriori measurement.
- **MOME archive + semantic git merge are components to build**, not free properties. "One elite per cell" only holds under the (cell × objective) keying; a naive text merge corrupts the archive.
- **EULA / Factorio ToS.** Headless is free but proprietary (Wube EULA); the DLC is account-bound. Running thousands of automated runs, or multi-instance on cloud, and *a fortiori* publishing results, requires checking the automated-use / multi-instance clauses.
- **Speedrun bounds are dated and non-interchangeable.** The TAS WR (1h21, 2020) is on Factorio 0.18 vanilla and not comparable to current play; there is no Space Age TAS. Human Any% records drift over time; any cited figure will silently go stale.
- **The Space Age DLC is paid** and required for DLC entities, both for generation (draftsman after update) and evaluation (headless). Phases 0-3 are designed to be feasible on free vanilla 2.0. Draftsman's Space Age support is an **inference** ("2.0" confirmed, "foundry/recycler" extrapolated) to verify in practice.
- **The "Wow for Nilaus" milestone targets the saturated vanilla terrain** (Phases 0-2), where beating the human is hardest; hence the non-comparative reframing. His actual terrain is Space Age (paid, Phase 5). The demonstrator's ambition must match the terrain it runs on.

## Sources

- [karpathy/autoresearch (GitHub)](https://github.com/karpathy/autoresearch) — autonomous LLM ML-research agent, the loop pattern.
- [Why everyone is talking about Karpathy's autonomous AI research agent (Fortune)](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/) — context and impact, the ~11% claim.
- [AlphaEvolve: A coding agent for scientific and algorithmic discovery (DeepMind PDF)](https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/AlphaEvolve.pdf) — the FunSearch → AlphaEvolve scientific lineage.
- [AlphaEvolve (arXiv 2506.13131)](https://ar5iv.labs.arxiv.org/html/2506.13131) — paper.
- [algorithmicsuperintelligence/openevolve (GitHub)](https://github.com/algorithmicsuperintelligence/openevolve) — open-source AlphaEvolve implementation, cascade evaluator + LLM ensemble + MAP-Elites island archive.
- [openevolve (PyPI)](https://pypi.org/project/openevolve/) — installation.
- [MAP-Elites / Quality-Diversity (emergentmind)](https://www.emergentmind.com/topics/map-elites-algorithm) — the algorithm that illuminates the space instead of seeking one optimum.
- [Quality-Diversity optimisation algorithms (reference site)](https://quality-diversity.github.io/) — QD corpus (incl. MOME, multi-objective MAP-Elites).
- [redruin1/factorio-draftsman (GitHub)](https://github.com/redruin1/factorio-draftsman) — programmatic blueprint manipulation, 2.0 support.
- [factorio-draftsman (PyPI)](https://pypi.org/project/factorio-draftsman/) — v3.3.0.
- [Factorio Learning Environment (GitHub)](https://github.com/JackHopkins/factorio-learning-environment) — RCON framework to drive Factorio with an LLM (relevant if moving to real-time control, level B).
- [FLE (arXiv 2503.09617)](https://arxiv.org/abs/2503.09617) — paper.
- [test-000001: What is the best way to benchmark Factorio? (mulark)](https://mulark.github.io/tests/test-000001/test-000001.html) — deterministic headless benchmark methodology, `--benchmark-ticks`.
- [Factorio — Speedrun.com](https://www.speedrun.com/factorio) — official leaderboards.
- [Any% 1:27:28 (Nefrums, speedrun.com)](https://www.speedrun.com/factorio/runs/m3742xdz) — human solo Any% (vanilla).
- [FFF#344 — Team Steelaxe 1:15:21](https://www.factorio.com/blog/post/fff-344) — human multiplayer Any%.
- [Any% TAS WR 1:21:20 (forums, 2020, v0.18)](https://forums.factorio.com/viewtopic.php?t=84276) — TAS WR, **vanilla 0.18, pre-Space-Age, not a current bound**.
- [AnyPctTAS — Factorio Mods](https://mods.factorio.com/mod/AnyPctTAS) — community TAS mod: the Campaign regime already done by hand, action-sequence format.
- [Factorio: Space Age — Speedrun.com](https://www.speedrun.com/Space_Age) — dedicated Space Age leaderboard (times of a different order of magnitude; **no Space Age TAS**).
- [Nilaus Cityblock 2.0 (factorio.school)](https://www.factorio.school/view/-OXRxN4v1U8dwIjSO4l4) — Nilaus's signature: codification/democratization of the city block via the Master Class.
- [Factorio Master Class — City Blocks & Rail Segments (FactorioBin)](https://factoriobin.com/post/Y52EhJ74/1) — grid-aligned 100×100 blueprint books.
- [Factorio Space Age MEGABASE — Nilaus (Patreon)](https://www.patreon.com/posts/factorio-space-134162958) — current work: True Megabase 1M+ SPM, space platforms, quality upcycling (technical details to deepen before contact).

## Voir aussi

- [[quatrieme-paradigme-big-data]] — the data-/simulation-driven research paradigm that frames this project epistemically (the evaluator-as-experiment).
- [[destruction-creatrice-technicite-recherche]] — innovation and technical research as creative destruction, the broader lens on "can the machine invent new methods?".

---

*Document issu de brain, le cerveau déporté de Géraud, assisté par Claude Opus 4.8.*
