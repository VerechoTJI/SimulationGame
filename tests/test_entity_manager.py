# tests/test_entity_manager.py
import pytest
import numpy as np
from unittest.mock import MagicMock, call

from domain.spatial_hash import SpatialHash
from domain.entity_manager import EntityManager
from domain.entity import Entity
from domain.human import Human
from domain.rice import Rice
from domain.sheep import Sheep  # Add new import


@pytest.fixture
def entity_manager(mock_config):
    """Provides a standard EntityManager initialized with the full mock config."""
    tile_size = mock_config["simulation"]["tile_size_meters"]
    return EntityManager(config_data=mock_config, tile_size=tile_size)


@pytest.fixture
def entity_manager_with_mock_hash(mock_config):
    """Provides an EntityManager with mocked SpatialHash objects."""
    tile_size = mock_config["simulation"]["tile_size_meters"]
    manager = EntityManager(config_data=mock_config, tile_size=tile_size)
    # Replace the real spatial hashes with mocks
    manager.spatial_hashes["human"] = MagicMock(spec=SpatialHash)
    manager.spatial_hashes["rice"] = MagicMock(spec=SpatialHash)
    manager.spatial_hashes["sheep"] = MagicMock(spec=SpatialHash)
    return manager


# ... (All tests before TestEntityManagerFindNearest are unchanged) ...
def test_initialization(entity_manager, mock_config):
    """Tests that the EntityManager initializes its data structures correctly."""
    assert len(entity_manager.entities) == 0

    # Check that pools and hashes were created for all entities in the config
    defined_entities = mock_config["entities"].keys()
    assert set(entity_manager.entity_pools.keys()) == set(defined_entities)
    assert set(entity_manager.spatial_hashes.keys()) == set(defined_entities)
    assert isinstance(entity_manager.spatial_hashes["human"], SpatialHash)


def test_create_entity(entity_manager):
    """Tests the generic create_entity method."""
    human = entity_manager.create_entity("human", pos_y=5, pos_x=6)
    assert isinstance(human, Human)
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is human
    assert human.position[0] == 55.0  # (5 + 0.5) * 10
    assert human.position[1] == 65.0  # (6 + 0.5) * 10


def test_create_entity_adds_to_spatial_hash(entity_manager_with_mock_hash):
    """Tests that creating an entity correctly adds it to its spatial hash."""
    manager = entity_manager_with_mock_hash
    mock_hash = manager.spatial_hashes["rice"]

    rice = manager.create_entity("rice", pos_y=1, pos_x=2)

    mock_hash.add.assert_called_once_with(rice)


def test_cleanup_removes_from_spatial_hash(entity_manager_with_mock_hash):
    """Tests that cleaning up dead entities removes them from their spatial hash."""
    manager = entity_manager_with_mock_hash
    mock_hash = manager.spatial_hashes["rice"]

    rice = manager.create_entity("rice", pos_y=2, pos_x=2)
    rice.is_eaten = True  # Mark for cleanup
    mock_hash.reset_mock()

    removed = manager.cleanup_dead_entities()

    assert len(removed) == 1
    assert removed[0] is rice
    mock_hash.remove.assert_called_once_with(rice)


def test_cleanup_returns_removed_entities(entity_manager):
    human = entity_manager.create_entity("human", pos_y=1, pos_x=1)
    rice = entity_manager.create_entity("human", pos_y=2, pos_x=2)
    human.age = 999
    removed = entity_manager.cleanup_dead_entities()
    assert len(removed) == 1
    assert removed[0] is human
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is rice


def test_update_entity_position_calls_hash_update(entity_manager_with_mock_hash):
    """Tests that the update method calls the correct spatial hash."""
    manager = entity_manager_with_mock_hash
    mock_human_hash = manager.spatial_hashes["human"]
    mock_rice_hash = manager.spatial_hashes["rice"]

    human = manager.create_entity("human", pos_y=1, pos_x=1)
    mock_human_hash.reset_mock()

    old_position = human.position.copy()
    new_position = np.array([55.0, 55.0])

    manager.update_entity_position(human, old_position, new_position)

    mock_human_hash.update.assert_called_once_with(human, old_position, new_position)
    mock_rice_hash.update.assert_not_called()


class TestEntityManagerFindNearest:
    @pytest.fixture
    def manager_for_find_test(self, mock_config):
        """A special manager with a config that makes sense for proximity tests."""
        # Use a deepcopy to avoid modifying the global mock_config
        import copy

        test_config = copy.deepcopy(mock_config)
        # --- THIS IS THE KEY ---
        # Make the world granular for this test so adjacent grid tiles are in adjacent cells
        test_config["simulation"]["tile_size_meters"] = 1
        test_config["performance"]["spatial_hash_cell_size"] = 2
        return EntityManager(config_data=test_config, tile_size=1)

    def test_find_nearest_entity_uses_spatial_hash(self, manager_for_find_test):
        # This test is now much simpler to reason about.
        manager = manager_for_find_test
        # Rice A is at world (1.5, 1.5)
        rice_A = manager.create_entity("rice", pos_y=1, pos_x=1)
        # Rice B is at world (3.5, 3.5)
        rice_B = manager.create_entity("rice", pos_y=3, pos_x=3)
        # Origin is closer to B
        origin_pos_yx = np.array([4.0, 4.0])

        found = manager.find_nearest_entity_in_vicinity(origin_pos_yx, Rice)
        assert found is not None
        assert found.id == rice_B.id

    def test_find_nearest_with_predicate(self, manager_for_find_test):
        # ARRANGE
        manager = manager_for_find_test
        # Origin is at (3.5, 3.5) -> Cell (1,1)
        origin_pos_yx = np.array([3.5, 3.5])

        # Unmatured rice is at (3.5, 2.5) -> Cell (1,1). Close but fails predicate.
        rice_unmatured = manager.create_entity("rice", pos_y=3, pos_x=2)
        rice_unmatured.age = 1

        # Matured rice is at (5.5, 5.5) -> Cell (2,2). Further but passes predicate.
        rice_matured = manager.create_entity("rice", pos_y=5, pos_x=5)
        rice_matured.age = rice_matured.mature_age

        # ACT
        found = manager.find_nearest_entity_in_vicinity(
            origin_pos_yx, Rice, predicate=lambda r: r.matured
        )

        # ASSERT
        assert found is not None, "A matured rice plant should have been found"
        assert found.id == rice_matured.id, "The matured rice should be selected"

    def test_returns_none_if_no_matching_entity_found(self, entity_manager):
        entity_manager.create_entity("human", pos_y=1, pos_x=1)
        origin_pos_yx = np.array([5.0, 5.0])
        found = entity_manager.find_nearest_entity_in_vicinity(origin_pos_yx, Rice)
        assert found is None

    def test_returns_none_if_no_entities_in_spatial_hash_vicinity(self, entity_manager):
        # ARRANGE
        # Cell size is 10. Origin is at (5,5) in cell (0,0).
        # Rice is at (55, 55) in cell (5,5), well outside the 3x3 search area.
        entity_manager.create_entity("rice", pos_y=5, pos_x=5)
        origin_pos_yx = np.array([5.0, 5.0])

        # ACT
        found = entity_manager.find_nearest_entity_in_vicinity(origin_pos_yx, Rice)

        # ASSERT
        assert found is None


class TestEntityManagerObjectPooling:
    def test_dying_entity_is_returned_to_pool(self, entity_manager):
        human = entity_manager.create_entity("human", pos_y=5, pos_x=5)
        human_id = human.id
        human.saturation = 0

        entity_manager.cleanup_dead_entities()

        assert len(entity_manager.entities) == 0
        assert len(entity_manager.entity_pools["human"]._pool) == 1
        pooled_human = entity_manager.entity_pools["human"]._pool[0]
        assert pooled_human.id == human_id

    def test_creating_entity_reuses_pooled_object(self, entity_manager):
        human1 = entity_manager.create_entity("human", pos_y=5, pos_x=5)
        dead_human_id = human1.id
        human1.saturation = 0
        entity_manager.cleanup_dead_entities()

        human2 = entity_manager.create_entity("human", pos_y=1, pos_x=1)

        assert len(entity_manager.entities) == 1
        assert len(entity_manager.entity_pools["human"]._pool) == 0
        assert human2.id == dead_human_id

    def test_recycled_entity_has_state_reset(self, entity_manager):
        human_to_die = entity_manager.create_entity("human", pos_y=5, pos_x=5)
        human_to_die.age = 50
        human_to_die.saturation = 0
        human_to_die_id = human_to_die.id
        entity_manager.cleanup_dead_entities()

        recycled_human = entity_manager.create_entity("human", pos_y=1, pos_x=2)

        assert recycled_human.id == human_to_die_id
        assert recycled_human.age == 0
        assert recycled_human.saturation == recycled_human.max_saturation


def test_create_sheep_from_config(entity_manager, mock_config):
    """
    Tests that the EntityManager can initialize a sheep pool from config
    and create a sheep entity.
    """
    # ARRANGE
    # Ensure the 'sheep' config is present for this test
    if "sheep" not in mock_config["entities"]:
        mock_config["entities"]["sheep"] = {
            "attributes": {
                "max_age": 1600,
                "move_speed": 0.5,
                "max_saturation": 80,
                "hungry_threshold": 40,
                "reproduction_threshold": 60,
                "reproduction_cost": 15,
                "reproduction_cooldown": 400,
                "newborn_saturation_endowment": 15,
            }
        }

    # Re-initialize the entity manager with the sheep config
    tile_size = mock_config["simulation"]["tile_size_meters"]
    manager = EntityManager(config_data=mock_config, tile_size=tile_size)

    # ACT
    sheep = manager.create_entity("sheep", pos_y=10, pos_x=12)

    # ASSERT
    assert "sheep" in manager.entity_pools
    assert "sheep" in manager.spatial_hashes
    assert isinstance(sheep, Sheep)
    assert len(manager.entities) == 1
    assert manager.entities[0] is sheep
    assert sheep.position[0] == 105.0  # (10 + 0.5) * 10
    assert sheep.position[1] == 125.0  # (12 + 0.5) * 10
