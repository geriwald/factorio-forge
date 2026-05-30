"""Phase 0, first link: blueprint strings decode to the right entities.

These tests use a draftsman-generated blueprint as ground truth (round-trip),
so they need no game binary and no hand-typed blueprint string.
"""

import pytest
from draftsman.blueprintable import Blueprint

from factorio_forge.blueprint import count_entities, entity_type_histogram


@pytest.fixture
def sample_blueprint_string() -> str:
    """A known blueprint: 2 transport belts + 1 inserter."""
    bp = Blueprint()
    bp.entities.append("transport-belt", tile_position=(0, 0))
    bp.entities.append("transport-belt", tile_position=(1, 0))
    bp.entities.append("inserter", tile_position=(2, 0))
    return bp.to_string()


def test_count_entities(sample_blueprint_string: str):
    assert count_entities(sample_blueprint_string) == 3


def test_entity_type_histogram(sample_blueprint_string: str):
    assert entity_type_histogram(sample_blueprint_string) == {
        "transport-belt": 2,
        "inserter": 1,
    }


def test_empty_blueprint():
    empty = Blueprint().to_string()
    assert count_entities(empty) == 0
    assert entity_type_histogram(empty) == {}
