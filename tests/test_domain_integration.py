# tests/test_domain_integration.py
import pytest
import numpy as np
import copy

from domain.human import Human
from domain.rice import Rice
from domain.sheep import Sheep
from domain.tile import TILES


class TestEcosystemIntegration:
    def test_world_can_tick_with_all_entity_types(self, world_no_spawn):
        world = world_no_spawn
        world.entity_manager.create_entity("human", pos_y=2, pos_x=2)
        world.entity_manager.create_entity("sheep", pos_y=3, pos_x=3)
        rice = world.entity_manager.create_entity("rice", pos_y=4, pos_x=4)
        rice.age = rice.mature_age - 1
        rice.max_age = 9999

        try:
            for _ in range(30):
                world.game_tick()
        except Exception as e:
            pytest.fail(f"World tick failed with multiple entities present: {e}")


class TestHumanAIIntegration:
    def test_hungry_human_obeys_flow_field_vector(self, world_factory):
        world = world_factory()
        flat_grid = [[TILES["land"]] * world.width for _ in range(world.height)]
        world.grid = flat_grid
        world.flow_field_manager.grid = flat_grid

        human = world.entity_manager.create_entity("human", pos_y=2, pos_x=2)
        human.saturation = human.is_hungry_threshold - 1
        rice = world.entity_manager.create_entity("rice", pos_y=7, pos_x=7)
        rice.age = rice.mature_age - 1
        rice.max_age = 9999

        world.game_tick()

        world.flow_field_manager.process_flow_field_update(
            node_budget=world.width * world.height * 8
        )
        while world.flow_field_manager.recalculation_in_progress:
            world.flow_field_manager.process_flow_field_update(
                node_budget=world.width * world.height * 8
            )
        while world.flow_field_manager.dirty_chunks:
            world.flow_field_manager.process_flow_field_update(node_budget=0)

        old_pos = human.position.copy()
        flow_vector = world.get_flow_vector_at_position(human.position)
        human.tick(world)
        new_pos = human.position
        assert not np.array_equal(old_pos, new_pos), "Human should have moved."
        assert np.array_equal(
            flow_vector, [1, 1]
        ), "Flow vector on a flat grid must point towards the goal."
        movement_vector = new_pos - old_pos
        assert np.all(
            np.sign(movement_vector) == np.sign(flow_vector)
        ), f"Human moved {movement_vector}, but flow was {flow_vector}"


class TestWorldFlowFieldIntegration:
    def test_flow_field_updates_incrementally_after_food_spawn(
        self, world_factory, world_no_spawn
    ):
        custom_config = copy.deepcopy(world_no_spawn.config)
        custom_config["performance"]["flow_field_node_budget"] = 10
        world = world_factory(custom_config=custom_config)
        flat_grid = [[TILES["land"]] * world.width for _ in range(world.height)]
        world.grid = flat_grid
        world.flow_field_manager.grid = flat_grid

        initial_flow_field = world.flow_field_manager.flow_field
        assert np.all(initial_flow_field == 0)

        rice = world.entity_manager.create_entity("rice", pos_y=7, pos_x=7)
        rice.age = rice.mature_age - 1
        rice.max_age = 9999

        # --- THE FINAL, DEFINITIVE, INCONTROVERTIBLE FIX ---
        # Tick 1: Rice matures, flags `recalculation_needed` as True.
        world.game_tick()
        assert not world.flow_field_manager.recalculation_in_progress
        assert world.flow_field_manager.recalculation_needed

        # Tick 2: FFM sees `recalculation_needed` flag and starts processing.
        world.game_tick()
        assert world.flow_field_manager.recalculation_in_progress

        # Tick N...: Finish the update. (100 tiles / budget of 10 = 10 ticks for cost + chunks)
        for _ in range(15):
            world.game_tick()

        final_flow_field = world.flow_field_manager.flow_field
        assert (
            not world.flow_field_manager.recalculation_in_progress
        ), "Recalculation should have finished."
        assert (
            not world.flow_field_manager.dirty_chunks
        ), "All chunks should have been processed."
        assert np.any(final_flow_field != 0), "Flow field should have non-zero vectors."
        vector_at_2_2 = world.get_flow_vector_at_position(np.array([25.0, 25.0]))
        assert np.array_equal(vector_at_2_2, [1, 1])
