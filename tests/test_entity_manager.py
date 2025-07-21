# tests/test_entity_manager.py

import pytest
import numpy as np
from domain.entity_manager import EntityManager
from domain.entity import Entity
from domain.human import Human
from domain.rice import Rice


@pytest.fixture
def entity_manager(mock_config):
    """Provides an EntityManager instance initialized with mock config."""
    tile_size = mock_config["simulation"]["tile_size_meters"]
    return EntityManager(config_data=mock_config, tile_size=tile_size)


def test_initialization(entity_manager):
    """Tests that the EntityManager initializes correctly."""
    assert len(entity_manager.entities) == 0
    assert entity_manager._human_pool is not None
    assert entity_manager._rice_pool is not None


def test_create_human(entity_manager):
    """Tests the creation of a Human entity."""
    human = entity_manager.create_human(x=5, y=5)
    assert isinstance(human, Human)
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is human
    assert human.position[0] == 55.0
    assert human.position[1] == 55.0


def test_create_rice(entity_manager):
    """Tests the creation of a Rice entity."""
    rice = entity_manager.create_rice(x=1, y=1)
    assert isinstance(rice, Rice)
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is rice
    assert rice.position[0] == 15.0
    assert rice.position[1] == 15.0


def test_cleanup_returns_removed_entities(entity_manager):
    """Tests that the cleanup method returns the list of entities it removed."""
    human = entity_manager.create_human(x=1, y=1)
    rice = entity_manager.create_rice(x=2, y=2)
    human.age = 999

    removed = entity_manager.cleanup_dead_entities()

    assert len(removed) == 1
    assert removed[0] is human
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is rice


# --- MOVED AND REFACTORED TESTS ---


class TestEntityManagerFindNearest:
    def test_find_nearest_entity(self, entity_manager, human, rice_plant):
        # ARRANGE
        # Use the manager to create entities in the correct state
        rice_close = entity_manager.create_rice(x=1, y=1)  # pos (15, 15)
        rice_far = entity_manager.create_rice(x=8, y=8)  # pos (85, 85)

        origin_pos = np.array([5.0, 5.0])

        # ACT
        found = entity_manager.find_nearest_entity(origin_pos, Rice)

        # ASSERT
        assert found is not None
        assert found.id == rice_close.id

    def test_find_nearest_with_predicate(self, entity_manager):
        # ARRANGE
        rice_close_unmatured = entity_manager.create_rice(x=1, y=1)
        rice_close_unmatured.age = 1  # Not mature

        rice_far_matured = entity_manager.create_rice(x=8, y=8)
        rice_far_matured.age = rice_far_matured.max_age  # Mature

        origin_pos = np.array([5.0, 5.0])

        # ACT
        found = entity_manager.find_nearest_entity(
            origin_pos, Rice, predicate=lambda r: r.matured
        )

        # ASSERT
        assert found is not None
        assert found.id == rice_far_matured.id

    def test_returns_none_if_no_matching_entity_found(self, entity_manager, human):
        # ARRANGE
        entity_manager.create_human(x=1, y=1)  # The only entity is a human
        origin_pos = np.array([5.0, 5.0])

        # ACT
        found = entity_manager.find_nearest_entity(origin_pos, Rice)

        # ASSERT
        assert found is None


class TestEntityManagerObjectPooling:
    def test_dying_entity_is_returned_to_pool(self, entity_manager):
        # ARRANGE
        human = entity_manager.create_human(x=5, y=5)
        human_id = human.id
        human.saturation = 0  # "Kill" the human

        assert len(entity_manager.entities) == 1
        assert len(entity_manager._human_pool._pool) == 0

        # ACT
        entity_manager.cleanup_dead_entities()

        # ASSERT
        assert len(entity_manager.entities) == 0
        assert len(entity_manager._human_pool._pool) == 1
        pooled_human = entity_manager._human_pool._pool[0]
        assert pooled_human.id == human_id

    def test_creating_entity_reuses_pooled_object(self, entity_manager):
        # ARRANGE
        # Create, kill, and clean up a human to populate the pool
        human1 = entity_manager.create_human(x=5, y=5)
        dead_human_id = human1.id
        human1.saturation = 0
        entity_manager.cleanup_dead_entities()

        assert len(entity_manager.entities) == 0
        assert len(entity_manager._human_pool._pool) == 1

        # ACT
        # Create a new human, which should come from the pool
        human2 = entity_manager.create_human(x=1, y=1)

        # ASSERT
        assert len(entity_manager.entities) == 1
        assert len(entity_manager._human_pool._pool) == 0
        assert human2.id == dead_human_id

    def test_recycled_entity_has_state_reset(self, entity_manager):
        # ARRANGE
        human_to_die = entity_manager.create_human(x=5, y=5)
        human_to_die.age = 50
        human_to_die.saturation = 0  # Kill it
        human_to_die_id = human_to_die.id
        entity_manager.cleanup_dead_entities()

        # ACT
        recycled_human = entity_manager.create_human(x=1, y=1)

        # ASSERT
        assert recycled_human.id == human_to_die_id
        assert recycled_human.age == 0, "Age should be reset"
        assert recycled_human.saturation == recycled_human.max_saturation
        # Check position was reset (1.5 * 10 = 15)
        assert recycled_human.position[0] == 15.0
