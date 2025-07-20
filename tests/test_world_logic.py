# tests/test_world_logic.py
import pytest
import numpy as np

from domain.world import World
from domain.rice import Rice
from domain.human import Human


@pytest.fixture
def world_instance(world_factory):
    """Provides a real, but blank, World instance."""
    # Using a real world instance is better for testing its methods

    return world_factory(width=10, height=10)


class TestWorldFindNearest:
    def test_find_nearest_entity(self, world_instance, rice_config, human):
        """Tests that the correct nearest entity is found."""
        rice_close = Rice(
            pos_x=15,
            pos_y=15,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )  # Grid (1,1)
        rice_far = Rice(
            pos_x=85,
            pos_y=85,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )  # Grid (8,8)
        human.posx = 25
        human.posy = 25
        world_instance.entities = [rice_close, rice_far, human]

        origin_pos = np.array([5.0, 5.0])  # Grid (0,0)

        # Action
        found = world_instance.find_nearest_entity(origin_pos, Rice)

        # Assertion
        assert found is not None
        assert found.id == rice_close.id

    def test_find_nearest_with_predicate(self, world_instance, rice_config):
        """Tests that the predicate correctly filters entities."""
        # This one is close but not mature
        rice_close_unmatured = Rice(
            pos_x=15,
            pos_y=15,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )
        rice_close_unmatured.age = 1

        # This one is far but is mature
        rice_far_matured = Rice(
            pos_x=85,
            pos_y=85,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )
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

    def test_returns_none_if_no_matching_entity_found(self, world_instance, human):
        """Tests that None is returned if no entities match the criteria."""
        human.pos_x = 15
        human.pos_y = 15
        world_instance.entities = [human]
        origin_pos = np.array([5.0, 5.0])

        # Action: Look for Rice, but there are only Humans
        found = world_instance.find_nearest_entity(origin_pos, Rice)

        # Assertion
        assert found is None


class TestWorldReproduction:
    def test_world_tick_spawns_new_human_from_reproduction(self, world_instance, human):
        # ARRANGE
        # 1. Place a human who is ready to reproduce in the world.
        parent = human
        parent.saturation = 100  # Well above the threshold
        parent.reproduction_cooldown = 0
        parent.position = np.array([55.0, 55.0])  # Grid (5, 5)

        world_instance.entities.append(parent)

        # Sanity check: ensure we start with exactly one entity.
        assert len(world_instance.entities) == 1

        # ACT
        # The world performs its logic for one tick.
        world_instance.game_tick()

        # ASSERT
        # 1. A new entity should have been created.
        assert (
            len(world_instance.entities) == 2
        ), "World should now contain two entities."

        # 2. Find the parent and the newborn from the entity list.
        all_humans = [e for e in world_instance.entities if isinstance(e, Human)]
        assert len(all_humans) == 2, "There should be two humans in the world."

        new_parent_state = next(p for p in all_humans if p.id == parent.id)
        newborn = next(n for n in all_humans if n.id != parent.id)

        # 3. Check the parent's state has been updated.
        assert new_parent_state.saturation == 49  # Correct expected saturation
        assert new_parent_state.reproduction_cooldown == 20  # Cooldown is now active

        # 4. Check the newborn's state.
        assert newborn.saturation == 40  # Endowed by parent

        # 5. Check the newborn's position is adjacent to the parent's.
        parent_grid_pos = (5, 5)
        newborn_grid_pos = world_instance.get_grid_position(newborn.position)

        dx = abs(parent_grid_pos[0] - newborn_grid_pos[0])
        dy = abs(parent_grid_pos[1] - newborn_grid_pos[1])
        assert (dx <= 1 and dy <= 1) and (
            dx + dy > 0
        ), "Newborn should be in an adjacent tile."
