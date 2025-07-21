# tests/test_domain_integration.py

import pytest
from domain.human import Human
from domain.rice import Rice

# Note: We use the `world_no_spawn` fixture from conftest.py
# This provides a fully assembled World with all its managers,
# a predictable map, and disabled random spawning, making it perfect
# for integration tests.


class TestHumanAIIntegration:
    """
    Tests the integration between a Human entity and the World systems
    it depends on (EntityManager, Pathfinder, etc.).
    """

    def test_hungry_human_finds_and_paths_to_food(self, world_no_spawn):
        """
        This test verifies the entire chain for a hungry human finding food.
        It simulates the exact scenario that revealed our previous bug.
        - Human.tick() is called.
        - Human._find_food_and_path() is called internally.
        - It must correctly call world.entity_manager.find_nearest_entity().
        - It must correctly call world.find_path().
        - If any link in this chain is broken, the test will fail.
        """
        # ARRANGE
        world = world_no_spawn

        # Place a human and make it hungry
        human = world.entity_manager.create_human(x=2, y=2)
        human.saturation = human.is_hungry_threshold - 1  # Make it hungry

        # Place a mature rice plant far away on a reachable tile
        rice = world.entity_manager.create_rice(x=7, y=7)
        rice.age = rice.max_age  # Make it mature

        # Pre-condition check
        assert len(human.path) == 0

        # ACT
        # This single call triggers all the integrated logic.
        human.tick(world)

        # ASSERT
        # The only proof we need is that the human successfully found a path.
        assert len(human.path) > 0, "Human should have found a path to the food."

        # Optional: More detailed check
        # Verify the path is heading towards the rice
        path_end_goal = human.path[-1]
        rice_grid_pos = world.get_grid_position(rice.position)
        assert (
            path_end_goal == rice_grid_pos
        ), "The path's destination should be the rice plant."
