# tests/test_entity_manager.py
import pytest
import numpy as np
from unittest.mock import MagicMock, call

from domain.spatial_hash import SpatialHash
from domain.entity_manager import EntityManager
from domain.entity import Entity
from domain.human import Human
from domain.rice import Rice


@pytest.fixture
def entity_manager(mock_config):
    tile_size = mock_config["simulation"]["tile_size_meters"]
    # Update config in-place for tests to use a predictable cell size
    mock_config["performance"]["spatial_hash_cell_size"] = 10
    return EntityManager(config_data=mock_config, tile_size=tile_size)


# ... (fixtures for mock_spatial_hash and entity_manager_with_mock_hash are unchanged) ...
@pytest.fixture
def mock_spatial_hash():
    """Provides a MagicMock for the SpatialHash."""
    return MagicMock(spec=SpatialHash)


@pytest.fixture
def entity_manager_with_mock_hash(mock_config, mock_spatial_hash):
    """Provides an EntityManager with a mocked SpatialHash for rice."""
    tile_size = mock_config["simulation"]["tile_size_meters"]
    manager = EntityManager(config_data=mock_config, tile_size=tile_size)
    manager._rice_spatial_hash = mock_spatial_hash
    manager._human_spatial_hash = mock_spatial_hash
    return manager


# ... (All tests before TestEntityManagerFindNearest are unchanged) ...
def test_initialization(entity_manager):
    assert len(entity_manager.entities) == 0
    assert entity_manager._human_pool is not None
    assert entity_manager._rice_pool is not None
    assert isinstance(entity_manager._rice_spatial_hash, SpatialHash)


def test_create_human(entity_manager):
    human = entity_manager.create_human(pos_y=5, pos_x=6)
    assert isinstance(human, Human)
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is human
    assert human.position[0] == 55.0
    assert human.position[1] == 65.0


def test_create_rice_adds_to_spatial_hash(entity_manager_with_mock_hash):
    manager = entity_manager_with_mock_hash
    mock_hash = manager._rice_spatial_hash
    rice = manager.create_rice(pos_y=1, pos_x=2)
    assert isinstance(rice, Rice)
    assert len(manager.entities) == 1
    assert manager.entities[0] is rice
    assert rice.position[0] == 15.0
    assert rice.position[1] == 25.0
    mock_hash.add.assert_called_once_with(rice)


def test_cleanup_removes_from_spatial_hash(entity_manager_with_mock_hash):
    manager = entity_manager_with_mock_hash
    mock_hash = manager._rice_spatial_hash
    rice = manager.create_rice(pos_y=2, pos_x=2)
    rice.age = 9999
    mock_hash.reset_mock()
    removed = manager.cleanup_dead_entities()
    assert len(removed) == 1
    assert removed[0] is rice
    mock_hash.remove.assert_called_once_with(rice)


def test_cleanup_returns_removed_entities(entity_manager):
    human = entity_manager.create_human(pos_y=1, pos_x=1)
    rice = entity_manager.create_rice(pos_y=2, pos_x=2)
    human.age = 999
    removed = entity_manager.cleanup_dead_entities()
    assert len(removed) == 1
    assert removed[0] is human
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is rice


def test_update_entity_position_calls_hash_update(entity_manager_with_mock_hash):
    manager = entity_manager_with_mock_hash
    mock_hash = manager._human_spatial_hash
    human = manager.create_human(pos_y=1, pos_x=1)
    mock_hash.reset_mock()
    old_position = human.position.copy()
    new_position = np.array([55.0, 55.0])
    manager.update_entity_position(human, old_position, new_position)
    mock_hash.update.assert_called_once_with(human, old_position, new_position)


class TestEntityManagerFindNearest:
    def test_find_nearest_entity_uses_spatial_hash(self, entity_manager):
        rice_close = entity_manager.create_rice(pos_y=1, pos_x=1)
        rice_mid = entity_manager.create_rice(pos_y=2, pos_x=2)
        rice_far = entity_manager.create_rice(pos_y=8, pos_x=8)
        entity_manager.create_human(pos_y=0, pos_x=0)
        origin_pos_yx = np.array([24.0, 24.0])
        found = entity_manager.find_nearest_entity(origin_pos_yx, Rice)
        assert found is not None
        assert (
            found.id == rice_mid.id
        ), "Should find the mathematically closest rice plant"

    def test_find_nearest_with_predicate(self, entity_manager):
        # ARRANGE
        # This rice is close, but does not satisfy the predicate
        rice_close_unmatured = entity_manager.create_rice(
            pos_y=1, pos_x=1
        )  # pos (15, 15)
        rice_close_unmatured.age = 1  # Not mature

        # This rice is a bit further, but IS mature and SHOULD be found
        rice_mid_matured = entity_manager.create_rice(pos_y=2, pos_x=2)  # pos (25, 25)
        rice_mid_matured.age = rice_mid_matured.mature_age  # Mature

        # This rice is mature, but OUTSIDE the search radius and should NOT be found
        rice_far_matured = entity_manager.create_rice(pos_y=8, pos_x=8)  # pos (85, 85)
        rice_far_matured.age = rice_far_matured.mature_age  # Mature

        # Search from (5,5). Cell size is 10. Search radius covers cells up to (y=1, x=1),
        # so world positions up to ~20.0 are included.
        # rice_mid_matured at (25, 25) is in cell (2,2), which is outside the 3x3 search grid.
        # Oh, let's adjust the test to be correct.
        # Search from (15, 15). Close is in (1,1), Mid is in (2,2). Both are searched.
        origin_pos_yx = np.array([16.0, 16.0])

        # ACT
        found = entity_manager.find_nearest_entity(
            origin_pos_yx, Rice, predicate=lambda r: r.matured
        )

        # ASSERT
        assert found is not None
        assert found.id == rice_mid_matured.id

    def test_returns_none_if_no_matching_entity_found(self, entity_manager):
        entity_manager.create_human(pos_y=1, pos_x=1)
        origin_pos_yx = np.array([5.0, 5.0])
        found = entity_manager.find_nearest_entity(origin_pos_yx, Rice)
        assert found is None

    def test_returns_none_if_no_entities_in_spatial_hash_vicinity(self, entity_manager):
        # ARRANGE
        # Cell size is 10. Origin is at (5,5) in cell (0,0).
        # Rice is at (55, 55) in cell (5,5), well outside the 3x3 search area.
        entity_manager.create_rice(pos_y=5, pos_x=5)
        origin_pos_yx = np.array([5.0, 5.0])

        # ACT
        found = entity_manager.find_nearest_entity(origin_pos_yx, Rice)

        # ASSERT
        assert found is None


# ... (TestEntityManagerObjectPooling is unchanged) ...
class TestEntityManagerObjectPooling:
    def test_dying_entity_is_returned_to_pool(self, entity_manager):
        human = entity_manager.create_human(pos_y=5, pos_x=5)
        human_id = human.id
        human.saturation = 0
        entity_manager.cleanup_dead_entities()
        assert len(entity_manager.entities) == 0
        assert len(entity_manager._human_pool._pool) == 1
        pooled_human = entity_manager._human_pool._pool[0]
        assert pooled_human.id == human_id

    def test_creating_entity_reuses_pooled_object(self, entity_manager):
        human1 = entity_manager.create_human(pos_y=5, pos_x=5)
        dead_human_id = human1.id
        human1.saturation = 0
        entity_manager.cleanup_dead_entities()
        human2 = entity_manager.create_human(pos_y=1, pos_x=1)
        assert len(entity_manager.entities) == 1
        assert len(entity_manager._human_pool._pool) == 0
        assert human2.id == dead_human_id

    def test_recycled_entity_has_state_reset(self, entity_manager):
        human_to_die = entity_manager.create_human(pos_y=5, pos_x=5)
        human_to_die.age = 50
        human_to_die.saturation = 0
        human_to_die_id = human_to_die.id
        entity_manager.cleanup_dead_entities()
        recycled_human = entity_manager.create_human(pos_y=1, pos_x=2)
        assert recycled_human.id == human_to_die_id
        assert recycled_human.age == 0, "Age should be reset"
        assert recycled_human.saturation == recycled_human.max_saturation
        assert recycled_human.position[0] == 15.0
        assert recycled_human.position[1] == 25.0
