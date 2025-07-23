# tests/test_world_logic.py
import pytest
import numpy as np

from domain.human import Human


@pytest.fixture
def world_instance(world_factory):
    """Provides a real, but blank, World instance."""
    return world_factory(width=10, height=10)


class TestWorldReproduction:
    def test_world_tick_spawns_new_human_from_reproduction(
        self, world_no_spawn, human_config
    ):
        # ARRANGE
        world = world_no_spawn

        # Use the entity manager with (y, x) to create the parent
        parent = world.entity_manager.create_human(pos_y=5, pos_x=5)
        # Manually set state for reproduction
        parent.saturation = 100
        parent.reproduction_cooldown = 0

        assert len(world.entity_manager.entities) == 1

        # ACT
        world.game_tick()

        # ASSERT
        entities = world.entity_manager.entities
        assert len(entities) == 2, "World should now contain two entities."

        all_humans = [e for e in entities if isinstance(e, Human)]
        assert len(all_humans) == 2

        new_parent_state = next(p for p in all_humans if p.id == parent.id)
        newborn = next(n for n in all_humans if n.id != parent.id)

        # Check parent's state change
        expected_parent_saturation = (
            100 - human_config["reproduction_cost"] - 1
        )  # cost - saturation decay
        assert new_parent_state.saturation == pytest.approx(expected_parent_saturation)
        assert new_parent_state.reproduction_cooldown > 0

        # Check newborn's state
        assert newborn.saturation == human_config["newborn_saturation_endowment"]

        # Check newborn's position
        parent_grid_pos = world.get_grid_position(parent.position)  # Returns (y, x)
        newborn_grid_pos = world.get_grid_position(newborn.position)  # Returns (y, x)

        # Correctly calculate dy and dx from the (y, x) tuples
        dy = abs(parent_grid_pos[0] - newborn_grid_pos[0])  # Difference in Y
        dx = abs(parent_grid_pos[1] - newborn_grid_pos[1])  # Difference in X

        assert (dx <= 1 and dy <= 1) and (
            dx + dy > 0
        ), "Newborn must be in an adjacent tile"
