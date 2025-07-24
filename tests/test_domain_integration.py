# tests/test_domain_integration.py
import pytest
import numpy as np
from domain.human import Human
from domain.rice import Rice
from domain.sheep import Sheep


class TestEcosystemIntegration:
    """
    High-level tests to ensure all entities can coexist and the world ticks.
    """

    def test_world_can_tick_with_all_entity_types(self, world_no_spawn):
        """
        A simple smoke test to ensure that a world populated with Humans,
        Sheep, and Rice can run for a few ticks without crashing.
        """
        # ARRANGE
        world = world_no_spawn
        world.entity_manager.create_entity("human", pos_y=2, pos_x=2)
        world.entity_manager.create_entity("sheep", pos_y=3, pos_x=3)
        rice = world.entity_manager.create_entity("rice", pos_y=4, pos_x=4)
        rice.age = rice.mature_age

        # ACT & ASSERT
        try:
            for _ in range(5):
                world.game_tick()
        except Exception as e:
            pytest.fail(f"World tick failed with multiple entities present: {e}")


class TestHumanAIIntegration:
    """
    Tests the integration between a Human entity and the World systems
    it depends on (FlowFieldManager, Pathfinder, etc.).
    """

    def test_hungry_human_obeys_flow_field_vector(self, world_no_spawn):
        # ARRANGE
        world = world_no_spawn
        # --- FIX: Use new entity creation method ---
        human = world.entity_manager.create_entity("human", pos_y=2, pos_x=2)
        human.saturation = human.is_hungry_threshold - 1

        # --- FIX: Use new entity creation method ---
        rice = world.entity_manager.create_entity("rice", pos_y=7, pos_x=7)
        rice.age = rice.mature_age

        # ... (rest of the test is unchanged) ...
        world._update_food_flow_field()
        assert np.any(world.food_flow_field)
        initial_pos_yx = human.position.copy()
        expected_flow_vector = world.get_flow_vector_at_position(initial_pos_yx)
        assert not np.all(expected_flow_vector == 0)
        normalized_expected_vector = expected_flow_vector / np.linalg.norm(
            expected_flow_vector
        )
        human.tick(world)
        final_pos_yx = human.position.copy()
        actual_move_vector = final_pos_yx - initial_pos_yx
        normalized_actual_vector = actual_move_vector / np.linalg.norm(
            actual_move_vector
        )
        assert not human.path
        assert np.allclose(normalized_actual_vector, normalized_expected_vector)

    def test_sated_human_wanders_using_astar_path(self, world_no_spawn):
        # ARRANGE
        world = world_no_spawn
        # --- FIX: Use new entity creation method ---
        human = world.entity_manager.create_entity("human", pos_y=2, pos_x=2)
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
        # --- FIX: Use new entity creation method ---
        rice = world.entity_manager.create_entity("rice", pos_y=5, pos_x=5)
        rice.age = rice.mature_age

        # ... (rest of the test is unchanged) ...
        world.game_tick()
        assert np.any(world.food_flow_field)
        assert world._ticks_since_flow_field_update == 0
        world.food_flow_field = np.zeros_like(world.food_flow_field)
        for _ in range(interval):
            rice.age = rice.mature_age
            world.game_tick()
        assert not np.any(world.food_flow_field)
        assert world._ticks_since_flow_field_update == interval
        rice.age = rice.mature_age
        world.game_tick()
        assert np.any(world.food_flow_field)
        assert world._ticks_since_flow_field_update == 0
