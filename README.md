# Factorio Forge

**Can an automated optimization loop discover Factorio production structures that humans wouldn't?**

Factorio Forge is a research project that applies LLM-driven quality-diversity search — in the lineage of Karpathy's *autoresearch* and DeepMind's FunSearch → AlphaEvolve — to Factorio factory design. Instead of seeking a single optimum (which collapses back onto the canonical, community-known designs), it uses **MAP-Elites** to *illuminate* the design space: an archipelago of high-performing, diverse, and sometimes unexpected solutions.

> Status: **early (Phase 0)** — building the evaluator. Not yet usable. See [`docs/design.md`](docs/design.md) for the full research framing.

## The idea in one picture

```
Claude (LLM) ──propose mutation──► Blueprint generator (draftsman)
     ▲                                      │ blueprint string
     │ scores, error traces                 ▼
     │                            Cascade evaluator
     │                            S1 valid · S2 builds · S3 headless benchmark
     │                                      │ score + behavior
     └──────────────────────────► MOME elite archive (cells × objective, git-versioned)
```

## Three nested regimes (artisanal naming)

| Regime | Name | Optimizes | Resources |
|--------|------|-----------|-----------|
| 1 | **Workshop** | one isolated block at steady state | idealized (infinity I/O) |
| 2 | **Workbench** | best achievable block given unlocked tech/quality | finite per tier |
| 3 | **Campaign** | the full from-zero progression sequence | finite, accumulating |

The **Catalog** links them: Workshop measures blocks in isolation, the Campaign plans over those measured contracts via a surrogate model (no full-game simulation).

## Objective-agnostic, multi-objective archive

Any objective can be the session's lead (throughput/SPM, compactness, aesthetics, robustness, human portability, **speedrun/TAS time**); the others are recorded *for information*. The git-versioned **MOME** (Multi-Objective MAP-Elites) archive is the central object — it is the diversity engine, the stepping-stone mechanism, and the collaborative substrate.

## Status & roadmap

- [ ] **Phase 0** — Evaluator feasibility: materialize a blueprint headless (no player), feed it, warm up, measure throughput reproducibly to <1%. *The make-or-break link.*
- [ ] **Phase 1** — Naive single-objective loop (autoresearch pattern).
- [ ] **Phase 2** — MAP-Elites first illumination + git archive.
- [ ] **Phase 2-bis** — Wow demonstrator (community diffusion milestone).
- [ ] **Phase 3** — Exotic metrics (robustness, aesthetics, energy density).
- [ ] **Phase 4** — Workshop → Campaign (surrogate + planning).
- [ ] **Phase 5** *(optional)* — Space Age.

## Requirements

- Python ≥ 3.10
- [`factorio-draftsman`](https://github.com/redruin1/factorio-draftsman) ≥ 3.3.0 (no game binary needed to generate/analyze)
- Factorio **headless** server (free, Linux) for the benchmark evaluator
- Factorio: Space Age DLC only for Phase 5

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE).

---

*Future home: `factorio-forge.com` (not yet registered). Built with Claude Code.*
