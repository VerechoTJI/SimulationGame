# tests/test_world_logic.py
import pytest
import numpy as np
import copy

from domain.world import World
from domain.rice import Rice
from domain.human import Human


@pytest.fixture
def world_instance(world_factory):
    """Provides a real, but blank, World instance."""
    return world_factory(width=10, height=10)


# A new fixture to provide a world with spawning disabled for deterministic tests
@pytest.fixture
def world_no_spawn(world_factory, mock_config):
    test_config = copy.deepcopy(mock_config)
    test_config["entities"]["rice"]["spawning"]["natural_spawn_chance"] = 0.0
    return world_factory(custom_config=test_config)


class TestWorldFindNearest:
    # ... (this class is unchanged) ...
    def test_find_nearest_entity(self, world_instance, rice_config, human):
        rice_close = Rice(
            pos_x=15,
            pos_y=15,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )
        rice_far = Rice(
            pos_x=85,
            pos_y=85,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )
        human.posx = 25
        human.posy = 25
        world_instance.entities = [rice_close, rice_far, human]
        origin_pos = np.array([5.0, 5.0])
        found = world_instance.find_nearest_entity(origin_pos, Rice)
        assert found is not None
        assert found.id == rice_close.id

    def test_find_nearest_with_predicate(self, world_instance, rice_config):
        rice_close_unmatured = Rice(
            pos_x=15,
            pos_y=15,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )
        rice_close_unmatured.age = 1
        rice_far_matured = Rice(
            pos_x=85,
            pos_y=85,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )
        rice_far_matured.age = rice_far_matured.max_age
        world_instance.entities = [rice_close_unmatured, rice_far_matured]
        origin_pos = np.array([5.0, 5.0])
        found = world_instance.find_nearest_entity(
            origin_pos, Rice, predicate=lambda r: r.matured
        )
        assert found is not None
        assert found.id == rice_far_matured.id

    def test_returns_none_if_no_matching_entity_found(self, world_instance, human):
        human.pos_x = 15
        human.pos_y = 15
        world_instance.entities = [human]
        origin_pos = np.array([5.0, 5.0])
        found = world_instance.find_nearest_entity(origin_pos, Rice)
        assert found is None


class TestWorldReproduction:
    def test_world_tick_spawns_new_human_from_reproduction(self, world_no_spawn, human):
        # ARRANGE
        # Use the world_no_spawn fixture for a deterministic test
        world_instance = world_no_spawn
        parent = human
        parent.saturation = 100
        parent.reproduction_cooldown = 0
        parent.position = np.array([55.0, 55.0])
        world_instance.entities.append(parent)
        assert len(world_instance.entities) == 1

        # ACT
        world_instance.game_tick()

        # ASSERT
        assert (
            len(world_instance.entities) == 2
        ), "World should now contain two entities."
        all_humans = [e for e in world_instance.entities if isinstance(e, Human)]
        assert len(all_humans) == 2
        new_parent_state = next(p for p in all_humans if p.id == parent.id)
        newborn = next(n for n in all_humans if n.id != parent.id)
        assert new_parent_state.saturation == 49
        assert new_parent_state.reproduction_cooldown == 20
        assert newborn.saturation == 40
        parent_grid_pos = (5, 5)
        newborn_grid_pos = world_instance.get_grid_position(newborn.position)
        dx = abs(parent_grid_pos[0] - newborn_grid_pos[0])
        dy = abs(parent_grid_pos[1] - newborn_grid_pos[1])
        assert (dx <= 1 and dy <= 1) and (dx + dy > 0)


class TestWorldObjectPooling:
    def test_dying_human_is_returned_to_pool(self, world_no_spawn):
        # Use world_no_spawn to prevent random rice from interfering
        world_instance = world_no_spawn
        world_instance.spawn_entity("human", 5, 5)
        human = world_instance.entities[0]
        human_id = human.id
        human.saturation = 1
        assert len(world_instance.entities) == 1
        assert len(world_instance._human_pool._pool) == 0

        world_instance.game_tick()

        assert len(world_instance.entities) == 0
        assert len(world_instance._human_pool._pool) == 1
        pooled_human = world_instance._human_pool._pool[0]
        assert pooled_human.id == human_id

    def test_spawning_human_reuses_pooled_object(self, world_no_spawn):
        world_instance = world_no_spawn
        world_instance.spawn_entity("human", 5, 5)
        dead_human_id = world_instance.entities[0].id
        world_instance.entities[0].saturation = 0
        world_instance.game_tick()
        assert len(world_instance.entities) == 0
        assert len(world_instance._human_pool._pool) == 1

        world_instance.spawn_entity("human", 1, 1)

        assert len(world_instance.entities) == 1
        assert len(world_instance._human_pool._pool) == 0
        recycled_human = world_instance.entities[0]
        assert recycled_human.id == dead_human_id

    def test_recycled_human_has_state_reset(self, world_no_spawn):
        # Use world_no_spawn to prevent random rice from interfering
        world_instance = world_no_spawn
        world_instance.spawn_entity("human", 5, 5)
        human_to_die = world_instance.entities[0]
        human_to_die.age = 50
        human_to_die.saturation = 0
        human_to_die_id = human_to_die.id
        world_instance.game_tick()

        world_instance.spawn_entity("human", 1, 1)

        # We need to correctly find the human, not just grab the first entity
        recycled_human = next(
            e for e in world_instance.entities if isinstance(e, Human)
        )

        assert (
            recycled_human.id == human_to_die_id
        ), "Should be the same object instance"
        assert recycled_human.age == 0, "Age should be reset to 0"
        assert recycled_human.saturation == recycled_human.max_saturation
        new_pos = world_instance.get_grid_position(recycled_human.position)
        assert new_pos == (1, 1)

    def test_eaten_rice_is_replanted_over_two_ticks(self, world_no_spawn):
        """Verify eaten rice is removed, pooled, and then replanted on the next tick."""
        world_instance = world_no_spawn
        # ARRANGE
        world_instance.spawn_entity("human", 1, 1)
        world_instance.spawn_entity("rice", 1, 1)
        human = next(e for e in world_instance.entities if isinstance(e, Human))
        original_rice = next(e for e in world_instance.entities if isinstance(e, Rice))
        human.saturation = 10
        original_rice.age = original_rice.max_age
        original_rice_id = original_rice.id
        original_rice_pos = original_rice.position.copy()

        # Pre-conditions
        assert len(world_instance.entities) == 2
        assert len(world_instance._rice_pool._pool) == 0
        assert len(world_instance.replant_queue) == 0

        # --- ACT 1: Rice is eaten ---
        world_instance.game_tick()

        # --- ASSERT 1: Rice is gone, pool has the object, queue is populated ---
        assert len(world_instance.entities) == 1, "Only the human should remain"
        assert not any(
            isinstance(e, Rice) for e in world_instance.entities
        ), "No rice should be active in the world"
        assert (
            len(world_instance._rice_pool._pool) == 1
        ), "The old rice object should be in the pool."
        assert (
            world_instance._rice_pool._pool[0].id == original_rice_id
        ), "The correct rice object was pooled."
        assert (
            len(world_instance.replant_queue) == 1
        ), "Location should be queued for replanting."

        # --- ACT 2: Replanting tick ---
        world_instance.game_tick()

        # --- ASSERT 2: A new rice plant has appeared ---
        assert (
            len(world_instance.entities) == 2
        ), "Should be a human and a new rice plant"
        assert (
            len(world_instance.replant_queue) == 0
        ), "Replant queue should be empty now"
        assert (
            len(world_instance._rice_pool._pool) == 0
        ), "Pool should be empty after object is reused for replanting"

        new_rice = next(
            (e for e in world_instance.entities if isinstance(e, Rice)), None
        )
        assert new_rice is not None, "A new rice plant should exist in the world."
        assert (
            new_rice.id == original_rice_id
        ), "The new rice should be the SAME recycled object."
        assert np.array_equal(
            new_rice.position, original_rice_pos
        ), "New rice should be in the same position."
        assert new_rice.age == 0, "Replanted rice should have its age reset to 0."
