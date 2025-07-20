# tests/test_world_helpers.py
import pytest
import numpy as np

from domain.world import World
from domain.rice import Rice
from domain.human import Human


@pytest.fixture
def world_instance():
    """Provides a real, but blank, World instance."""
    # Using a real world instance is better for testing its methods
    return World(width=10, height=10, tile_size=10)


class TestWorldFindNearest:
    def test_find_nearest_entity(self, world_instance):
        """Tests that the correct nearest entity is found."""
        rice_close = Rice(pos_x=15, pos_y=15)  # Grid (1,1)
        rice_far = Rice(pos_x=85, pos_y=85)  # Grid (8,8)
        human_entity = Human(pos_x=25, pos_y=25)  # Another entity type

        world_instance.entities = [rice_close, rice_far, human_entity]

        origin_pos = np.array([5.0, 5.0])  # Grid (0,0)

        # Action
        found = world_instance.find_nearest_entity(origin_pos, Rice)

        # Assertion
        assert found is not None
        assert found.id == rice_close.id

    def test_find_nearest_with_predicate(self, world_instance):
        """Tests that the predicate correctly filters entities."""
        # This one is close but not mature
        rice_close_unmatured = Rice(pos_x=15, pos_y=15)
        rice_close_unmatured.age = 1

        # This one is far but is mature
        rice_far_matured = Rice(pos_x=85, pos_y=85)
        rice_far_matured.age = rice_far_matured.max_age

        world_instance.entities = [rice_close_unmatured, rice_far_matured]
        origin_pos = np.array([5.0, 5.0])

        # Action: find the nearest MATURE rice
        found = world_instance.find_nearest_entity(
            origin_pos, Rice, predicate=lambda r: r.matured
        )

        # Assertion
        assert found is not None
        assert found.id == rice_far_matured.id

    def test_returns_none_if_no_matching_entity_found(self, world_instance):
        """Tests that None is returned if no entities match the criteria."""
        world_instance.entities = [Human(pos_x=15, pos_y=15)]
        origin_pos = np.array([5.0, 5.0])

        # Action: Look for Rice, but there are only Humans
        found = world_instance.find_nearest_entity(origin_pos, Rice)

        # Assertion
        assert found is None
