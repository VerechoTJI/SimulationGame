# tests/test_entity_manager.py

import pytest
from domain.entity_manager import EntityManager
from domain.human import Human
from domain.rice import Rice
from domain.entity import Entity


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
    # Verify position was converted from grid to world coords
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


def test_object_pooling_reuse(entity_manager):
    """Tests that dead entities are returned to the pool and reused."""
    # Create a human, get its ID
    human1 = entity_manager.create_human(x=1, y=1)
    human1_id = human1.id

    # "Kill" the human so it will be cleaned up
    human1.saturation = 0
    assert not human1.is_alive()

    # Run cleanup, which should release the object back to the pool
    entity_manager.cleanup_dead_entities()
    assert len(entity_manager.entities) == 0
    # The internal pool should now have one object
    assert len(entity_manager._human_pool._pool) == 1

    # Create a new human
    human2 = entity_manager.create_human(x=2, y=2)
    # The internal pool should now be empty again
    assert len(entity_manager._human_pool._pool) == 0

    # Assert it's the same object by checking the ID
    assert human2.id == human1_id
    # Assert its state was correctly reset
    assert human2.position[0] == 25.0
    assert human2.saturation > 0


def test_cleanup_returns_removed_entities(entity_manager):
    """Tests that the cleanup method returns the list of entities it removed."""
    human = entity_manager.create_human(x=1, y=1)
    rice = entity_manager.create_rice(x=2, y=2)

    # "Kill" only the human
    human.age = 999

    removed = entity_manager.cleanup_dead_entities()

    assert len(removed) == 1
    assert removed[0] is human
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is rice


def test_find_nearest_entity(entity_manager):
    """Tests the logic for finding the nearest entity."""
    rice1 = entity_manager.create_rice(x=1, y=1)  # at (15, 15)
    rice2 = entity_manager.create_rice(x=9, y=9)  # at (95, 95)
    human = entity_manager.create_human(x=2, y=2)  # at (25, 25)

    origin_pos = human.position

    # Find nearest of any type
    nearest = entity_manager.find_nearest_entity(origin_pos, entity_type=Entity)
    assert isinstance(nearest, Human)

    # Find nearest Rice
    nearest_rice = entity_manager.find_nearest_entity(origin_pos, entity_type=Rice)
    assert nearest_rice is rice1

    # Test with predicate (e.g., find only matured rice)
    rice1.age = 0  # Not mature
    rice2.age = rice2.max_age  # Mature

    nearest_matured_rice = entity_manager.find_nearest_entity(
        origin_pos, entity_type=Rice, predicate=lambda r: r.matured
    )
    assert nearest_matured_rice is rice2
