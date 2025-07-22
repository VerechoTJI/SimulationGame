import pytest
import numpy as np
from domain.human import Human
from domain.rice import Rice


# ... (TestHumanAIIntegration class is unchanged) ...
class TestHumanAIIntegration:
    """
    Tests the integration between a Human entity and the World systems
    it depends on (FlowFieldManager, Pathfinder, etc.).
    """

    def test_hungry_human_moves_towards_food_via_flow_field(self, world_no_spawn):
        """
        Verifies that a hungry human uses the World's flow field.
        """
        # ARRANGE
        world = world_no_spawn

        human = world.entity_manager.create_human(x=2, y=2)
        human.saturation = human.is_hungry_threshold - 1  # Make hungry
        initial_position = human.position.copy()

        rice = world.entity_manager.create_rice(x=7, y=7)
        rice.age = rice.mature_age

        # Pre-condition check
        assert len(human.path) == 0

        # ACT
        # The World's game_tick orchestrates flow field generation and entity updates.
        world.game_tick()

        # ASSERT
        assert np.any(world.food_flow_field), "Flow field should be generated"
        assert not human.path, "Hungry human should NOT have an A* path"
        assert human.position[0] > initial_position[0], "Human should move towards food"

    def test_sated_human_wanders_using_astar_path(self, world_no_spawn):
        """
        Verifies that a sated (not hungry) human falls back to the old
        A* pathfinding for wandering.
        """
        # ARRANGE
        world = world_no_spawn

        human = world.entity_manager.create_human(x=2, y=2)
        human.saturation = human.is_hungry_threshold + 20  # Make sated
        assert not human.path, "Human should start with no path"

        # ACT
        # A world tick will trigger the human's tick, which should generate a path.
        world.game_tick()

        # ASSERT
        assert human.path, "Sated human should have generated an A* path to wander"
        assert len(human.path) > 0, "The generated path should not be empty"


class TestWorldFlowFieldIntegration:
    """
    Tests the World's ability to orchestrate the FlowFieldManager correctly.
    """

    def test_world_generates_food_flow_field_periodically(self, world_no_spawn):
        # ARRANGE
        world = world_no_spawn
        interval = world._flow_field_update_interval

        rice = world.entity_manager.create_rice(x=5, y=5)
        rice.age = rice.mature_age

        # ACT 1: Tick once. The field should be generated on the first tick.
        world.game_tick()

        # ASSERT 1: Verify initial generation
        assert np.any(
            world.food_flow_field
        ), "Flow field should have generated on first tick."
        assert (
            world._ticks_since_flow_field_update == 0
        ), "Timer should be reset to 0 after generation."

        # ARRANGE 2: Manually reset the field to test the timer.
        world.food_flow_field = np.zeros_like(world.food_flow_field)

        # ACT 2: Tick until just before the next update is due.
        for _ in range(interval):
            # --- FIX: Keep the rice from dying of old age ---
            rice.age = rice.mature_age
            world.game_tick()

        # ASSERT 2: The field should NOT have regenerated yet.
        assert not np.any(
            world.food_flow_field
        ), "Flow field should not update before the interval is reached."
        assert world._ticks_since_flow_field_update == interval

        # ACT 3: Tick one more time to hit the interval.
        world.game_tick()

        # ASSERT 3: The field should now be regenerated.
        assert np.any(
            world.food_flow_field
        ), "Flow field should have regenerated after the interval."
        assert world._ticks_since_flow_field_update == 0
