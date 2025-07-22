# tests/test_domain_integration.py

import pytest
import numpy as np  # <-- Import numpy for array checks
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
        rice.age = rice.mature_age  # Make it mature

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


class TestWorldFlowFieldIntegration:
    """
    Tests the World's ability to orchestrate the FlowFieldManager correctly.
    """

    def test_world_generates_food_flow_field_periodically(self, world_no_spawn):
        # ARRANGE
        world = world_no_spawn
        interval = world._flow_field_update_interval

        # Place a mature rice plant to act as a goal
        rice = world.entity_manager.create_rice(x=5, y=5)
        rice.age = rice.mature_age  # Make it mature

        # Pre-condition: Flow field should be all zeros initially.
        assert not np.any(world.food_flow_field)

        # ACT 1: Tick once. The field should be generated on the first tick.
        world.game_tick()

        # ASSERT 1
        # The flow field should now be populated.
        assert np.any(
            world.food_flow_field
        ), "Flow field should have been generated on first tick."

        # Check a vector near the rice. From (4,4), vector should be (1,1) -> SE
        vector_at_4_4 = world.food_flow_field[4, 4]

        assert np.array_equal(
            vector_at_4_4, [1, 1]
        ), "Vector at (4,4) should point SE towards (5,5)"

        # ARRANGE 2: Manually reset the field to test the timer.
        world.food_flow_field = np.zeros_like(world.food_flow_field)
        assert world._ticks_since_flow_field_update == 0  # After one tick

        # ACT 2: Tick until just before the next update is due.
        for _ in range(interval):
            world.game_tick()
            rice.age = rice.mature_age

        # ASSERT 2: The field should STILL be empty.
        assert np.all(
            world.food_flow_field == 0
        ), "Flow field should not update before the interval is reached."

        # ACT 3: Tick one more time to hit the interval.
        world.game_tick()
        assert world._ticks_since_flow_field_update == 0  # After one tick

        # ASSERT 3: The field should now be regenerated.
        assert np.any(
            world.food_flow_field
        ), "Flow field should have regenerated after the interval."
        vector_at_4_4_after_interval = world.food_flow_field[4, 4]
        assert np.array_equal(
            vector_at_4_4_after_interval, [1, 1]
        ), "Vector should be correct after interval regeneration."
