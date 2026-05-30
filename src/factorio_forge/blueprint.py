"""Blueprint decoding helpers built on factorio-draftsman.

This is the very first link of the Phase 0 chain: take a Factorio blueprint
string and inspect its contents (entity count, types). It requires no game
binary — draftsman ships its own prototype data.
"""

from __future__ import annotations

from collections import Counter

from draftsman.blueprintable import get_blueprintable_from_string


def count_entities(blueprint_string: str) -> int:
    """Return the number of entities in a Factorio blueprint string.

    Args:
        blueprint_string: A Factorio blueprint export string (base64 + zlib + JSON).

    Returns:
        The count of entities placed in the blueprint.
    """
    blueprintable = get_blueprintable_from_string(blueprint_string)
    return len(blueprintable.entities)


def entity_type_histogram(blueprint_string: str) -> dict[str, int]:
    """Return a mapping of entity name -> count for a blueprint string."""
    blueprintable = get_blueprintable_from_string(blueprint_string)
    return dict(Counter(entity.name for entity in blueprintable.entities))
