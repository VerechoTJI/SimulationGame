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
    """Tests the creation of a Human entity using (y, x) grid coordinates."""
    # ARRANGE & ACT: Call with (pos_y, pos_x)
    human = entity_manager.create_human(pos_y=5, pos_x=6)

    # ASSERT
    assert isinstance(human, Human)
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is human
    # Assert world position is correct: position[0] = y, position[1] = x
    # pos_y = (5 + 0.5) * 10 = 55.0
    # pos_x = (6 + 0.5) * 10 = 65.0
    assert human.position[0] == 55.0
    assert human.position[1] == 65.0


def test_create_rice(entity_manager):
    """Tests the creation of a Rice entity using (y, x) grid coordinates."""
    # ARRANGE & ACT: Call with (pos_y, pos_x)
    rice = entity_manager.create_rice(pos_y=1, pos_x=2)

    # ASSERT
    assert isinstance(rice, Rice)
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is rice
    # Assert world position is correct: position[0] = y, position[1] = x
    # pos_y = (1 + 0.5) * 10 = 15.0
    # pos_x = (2 + 0.5) * 10 = 25.0
    assert rice.position[0] == 15.0
    assert rice.position[1] == 25.0


def test_cleanup_returns_removed_entities(entity_manager):
    """Tests that the cleanup method returns the list of entities it removed."""
    human = entity_manager.create_human(pos_y=1, pos_x=1)
    rice = entity_manager.create_rice(pos_y=2, pos_x=2)
    human.age = 999  # "Kill" the human

    removed = entity_manager.cleanup_dead_entities()

    assert len(removed) == 1
    assert removed[0] is human
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is rice


class TestEntityManagerFindNearest:
    def test_find_nearest_entity(self, entity_manager):
        # ARRANGE
        # world position is grid_pos * 10 + 5
        rice_close = entity_manager.create_rice(pos_y=1, pos_x=1)  # world_pos (15, 15)
        entity_manager.create_rice(pos_y=8, pos_x=8)  # world_pos (85, 85)
        origin_pos_yx = np.array([5.0, 5.0])  # y=5, x=5

        # ACT
        found = entity_manager.find_nearest_entity(origin_pos_yx, Rice)

        # ASSERT
        assert found is not None
        assert found.id == rice_close.id

    def test_find_nearest_with_predicate(self, entity_manager):
        # ARRANGE
        rice_close_unmatured = entity_manager.create_rice(pos_y=1, pos_x=1)
        rice_close_unmatured.age = 1  # Not mature

        rice_far_matured = entity_manager.create_rice(pos_y=8, pos_x=8)
        rice_far_matured.age = rice_far_matured.mature_age  # Mature

        origin_pos_yx = np.array([5.0, 5.0])  # y=5, x=5

        # ACT
        found = entity_manager.find_nearest_entity(
            origin_pos_yx, Rice, predicate=lambda r: r.matured
        )

        # ASSERT
        assert found is not None
        assert found.id == rice_far_matured.id

    def test_returns_none_if_no_matching_entity_found(self, entity_manager):
        # ARRANGE
        entity_manager.create_human(pos_y=1, pos_x=1)  # The only entity is a human
        origin_pos_yx = np.array([5.0, 5.0])

        # ACT
        found = entity_manager.find_nearest_entity(origin_pos_yx, Rice)

        # ASSERT
        assert found is None


class TestEntityManagerObjectPooling:
    def test_dying_entity_is_returned_to_pool(self, entity_manager):
        # ARRANGE
        human = entity_manager.create_human(pos_y=5, pos_x=5)
        human_id = human.id
        human.saturation = 0  # "Kill" the human

        # ACT
        entity_manager.cleanup_dead_entities()

        # ASSERT
        assert len(entity_manager.entities) == 0
        assert len(entity_manager._human_pool._pool) == 1
        pooled_human = entity_manager._human_pool._pool[0]
        assert pooled_human.id == human_id

    def test_creating_entity_reuses_pooled_object(self, entity_manager):
        # ARRANGE
        human1 = entity_manager.create_human(pos_y=5, pos_x=5)
        dead_human_id = human1.id
        human1.saturation = 0
        entity_manager.cleanup_dead_entities()

        # ACT
        human2 = entity_manager.create_human(pos_y=1, pos_x=1)

        # ASSERT
        assert len(entity_manager.entities) == 1
        assert len(entity_manager._human_pool._pool) == 0
        assert human2.id == dead_human_id

    def test_recycled_entity_has_state_reset(self, entity_manager):
        # ARRANGE
        human_to_die = entity_manager.create_human(pos_y=5, pos_x=5)
        human_to_die.age = 50
        human_to_die.saturation = 0  # Kill it
        human_to_die_id = human_to_die.id
        entity_manager.cleanup_dead_entities()

        # ACT
        recycled_human = entity_manager.create_human(pos_y=1, pos_x=2)

        # ASSERT
        assert recycled_human.id == human_to_die_id
        assert recycled_human.age == 0, "Age should be reset"
        assert recycled_human.saturation == recycled_human.max_saturation
        # Check position was reset: pos_y=(1+0.5)*10=15, pos_x=(2+0.5)*10=25
        assert recycled_human.position[0] == 15.0
        assert recycled_human.position[1] == 25.0
