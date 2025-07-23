# tests/test_domain_integration.py
import pytest
import numpy as np
from domain.human import Human
from domain.rice import Rice


class TestHumanAIIntegration:
    """
    Tests the integration between a Human entity and the World systems
    it depends on (FlowFieldManager, Pathfinder, etc.).
    """

    def test_hungry_human_obeys_flow_field_vector(self, world_no_spawn):
        """
        Verifies that a hungry human's movement directly corresponds to the
        flow field vector at its position, regardless of map layout.
        """
        # ARRANGE
        world = world_no_spawn
        human = world.entity_manager.create_human(pos_y=2, pos_x=2)
        human.saturation = human.is_hungry_threshold - 1

        rice = world.entity_manager.create_rice(pos_y=7, pos_x=7)
        rice.age = rice.mature_age

        # Manually generate the flow field to inspect it before the human moves.
        world._update_food_flow_field()
        assert np.any(
            world.food_flow_field
        ), "Flow field should be generated for test setup"

        # Get the vector the human SHOULD follow.
        initial_pos_yx = human.position.copy()
        expected_flow_vector = world.get_flow_vector_at_position(initial_pos_yx)

        # Ensure there is a path to follow for this test.
        assert not np.all(
            expected_flow_vector == 0
        ), "Test setup invalid: human has no path to food"

        # Normalize for direction comparison.
        normalized_expected_vector = expected_flow_vector / np.linalg.norm(
            expected_flow_vector
        )

        # ACT
        # The human's tick will use the pre-calculated flow field.
        human.tick(world)
        final_pos_yx = human.position.copy()

        # Calculate the vector of the actual movement.
        actual_move_vector = final_pos_yx - initial_pos_yx
        normalized_actual_vector = actual_move_vector / np.linalg.norm(
            actual_move_vector
        )

        # ASSERT
        assert not human.path, "Hungry human should NOT have an A* path"
        # Check that the direction of movement matches the flow field's direction.
        # np.allclose is used to handle potential floating point inaccuracies.
        assert np.allclose(
            normalized_actual_vector, normalized_expected_vector
        ), "Human's movement direction did not match the flow field vector"

    def test_sated_human_wanders_using_astar_path(self, world_no_spawn):
        """
        Verifies that a sated (not hungry) human falls back to the old
        A* pathfinding for wandering.
        """
        # ARRANGE
        world = world_no_spawn
        human = world.entity_manager.create_human(pos_y=2, pos_x=2)
        human.saturation = human.is_hungry_threshold + 20
        assert not human.path, "Human should start with no path"

        # ACT
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
        rice = world.entity_manager.create_rice(pos_y=5, pos_x=5)
        rice.age = rice.mature_age

        # ACT 1
        world.game_tick()
        # ASSERT 1
        assert np.any(world.food_flow_field)
        assert world._ticks_since_flow_field_update == 0

        # ARRANGE 2
        world.food_flow_field = np.zeros_like(world.food_flow_field)

        # ACT 2
        for _ in range(interval):
            rice.age = rice.mature_age
            world.game_tick()
        # ASSERT 2
        assert not np.any(world.food_flow_field)
        assert world._ticks_since_flow_field_update == interval

        # ACT 3
        rice.age = rice.mature_age
        world.game_tick()
        # ASSERT 3
        assert np.any(world.food_flow_field)
        assert world._ticks_since_flow_field_update == 0
