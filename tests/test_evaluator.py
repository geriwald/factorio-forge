"""Phase 0, the make-or-break link: player-less headless materialization.

These tests drive the real Factorio binary headless. They are the red->green
cycle on the Python harness (the Lua scenario is exercised through it, not in
isolation). They are skipped automatically when no Factorio binary is found, so
the suite stays green on machines without the game; the materialization proof
only holds where the binary runs.

Toy case: an iron-plate smelting lane (infinity-chest ore in, electric furnace,
iron plates out). Smallest case exercising materialize -> feed -> warm up ->
measure.
"""

from __future__ import annotations

import pytest
from draftsman.blueprintable import Blueprint

from factorio_forge.evaluator import factorio_binary, measure_throughput

pytestmark = pytest.mark.skipif(
    factorio_binary() is None,
    reason="no Factorio binary found; headless materialization cannot be proven here",
)


@pytest.fixture
def toy_smelting_blueprint() -> str:
    """An electrically-complete iron-ore -> electric-furnace -> iron-plate lane.

    The blueprint carries its own power network (a medium-electric-pole wired to
    an electric-energy-interface): electrical supply is part of the design, not
    something the scenario fakes. The Lua scenario applies only the run-time feed
    (infinity-chest source filter, infinite power) at materialization time.

    Inserter direction is the PICKUP side in 2.0: West means pick from the west
    tile (the upstream chest/furnace) and drop to the east, giving a west->east
    flow source-chest -> furnace -> sink-chest.
    """
    bp = Blueprint()
    bp.label = "phase0-toy-iron-smelting"
    bp.entities.append("infinity-chest", tile_position=(0, 1))
    bp.entities.append("fast-inserter", tile_position=(1, 1), direction=12)
    bp.entities.append("electric-furnace", tile_position=(2, 0))
    bp.entities.append("fast-inserter", tile_position=(5, 1), direction=12)
    bp.entities.append("infinity-chest", tile_position=(6, 1))
    bp.entities.append("medium-electric-pole", tile_position=(3, 4))
    bp.entities.append("electric-energy-interface", tile_position=(0, 4))
    return bp.to_string()


def test_measure_throughput_returns_positive_float(toy_smelting_blueprint: str):
    """AC1: the harness materializes the toy blueprint and returns a plates/s float."""
    rate = measure_throughput(toy_smelting_blueprint, item="iron-plate")
    assert isinstance(rate, float)
    assert rate > 0.0, "a fed, warmed-up smelting lane must produce iron plates"


def test_measure_throughput_reproducible_under_1pct(toy_smelting_blueprint: str):
    """AC2: the figure is reproducible to <1% across runs (the Phase 0 criterion)."""
    rates = [measure_throughput(toy_smelting_blueprint, item="iron-plate") for _ in range(3)]
    spread = (max(rates) - min(rates)) / (sum(rates) / len(rates))
    assert spread < 0.01, f"throughput not reproducible to <1%: {rates} (spread {spread:.4f})"
