# tests/test_entity_manager.py
import pytest
import numpy as np
from unittest.mock import MagicMock, call, patch

from domain.spatial_hash import SpatialHash
from domain.entity_manager import EntityManager
from domain.entity import Entity
from domain.human import Human
from domain.rice import Rice
from domain.sheep import Sheep


@pytest.fixture
def entity_manager(mock_config):
    tile_size = mock_config["simulation"]["tile_size_meters"]
    return EntityManager(config_data=mock_config, tile_size=tile_size)


@pytest.fixture
def entity_manager_with_mock_hash(mock_config):
    tile_size = mock_config["simulation"]["tile_size_meters"]
    manager = EntityManager(config_data=mock_config, tile_size=tile_size)
    manager.spatial_hashes["human"] = MagicMock(spec=SpatialHash)
    manager.spatial_hashes["rice"] = MagicMock(spec=SpatialHash)
    manager.spatial_hashes["sheep"] = MagicMock(spec=SpatialHash)
    return manager


# --- CORRECTED TESTS FOR FLOW FIELD NOTIFICATION ---


def test_create_rice_does_not_notify_flow_field_manager(mock_config):
    """
    Tests that creating a Rice entity does NOT notify the FlowFieldManager.
    This responsibility was moved to the Rice entity's tick() method.
    """
    # ARRANGE
    tile_size = mock_config["simulation"]["tile_size_meters"]
    manager = EntityManager(config_data=mock_config, tile_size=tile_size)
    mock_ffm = MagicMock()
    manager.flow_field_manager = mock_ffm

    # ACT
    manager.create_entity("rice", pos_y=3, pos_x=7)

    # ASSERT
    mock_ffm.add_goal.assert_not_called()


def test_cleanup_dead_rice_notifies_flow_field_manager(mock_config):
    """
    Tests that cleaning up a dead Rice entity correctly calls remove_goal on
    the FlowFieldManager, as this is the EntityManager's responsibility.
    """
    # ARRANGE
    tile_size = mock_config["simulation"]["tile_size_meters"]
    manager = EntityManager(config_data=mock_config, tile_size=tile_size)
    mock_ffm = MagicMock()
    manager.flow_field_manager = mock_ffm

    rice_plant = manager.create_entity("rice", pos_y=3, pos_x=7)
    rice_plant.is_eaten = True  # Mark it for cleanup

    # ACT
    manager.cleanup_dead_entities()

    # ASSERT
    mock_ffm.remove_goal.assert_called_once_with((3, 7))


def test_initialization(entity_manager, mock_config):
    assert len(entity_manager.entities) == 0
    defined_entities = mock_config["entities"].keys()
    assert set(entity_manager.entity_pools.keys()) == set(defined_entities)
    assert set(entity_manager.spatial_hashes.keys()) == set(defined_entities)
    assert isinstance(entity_manager.spatial_hashes["human"], SpatialHash)


def test_create_entity(entity_manager):
    human = entity_manager.create_entity("human", pos_y=5, pos_x=6)
    assert isinstance(human, Human)
    assert len(entity_manager.entities) == 1
    assert entity_manager.entities[0] is human
    assert human.position[0] == 55.0
    assert human.position[1] == 65.0


def test_create_entity_adds_to_spatial_hash(entity_manager_with_mock_hash):
    manager = entity_manager_with_mock_hash
    mock_hash = manager.spatial_hashes["rice"]
    rice = manager.create_entity("rice", pos_y=1, pos_x=2)
    mock_hash.add.assert_called_once_with(rice)


def test_cleanup_removes_from_spatial_hash(entity_manager_with_mock_hash):
    manager = entity_manager_with_mock_hash
    mock_hash = manager.spatial_hashes["rice"]
    rice = manager.create_entity("rice", pos_y=2, pos_x=2)
    rice.is_eaten = True
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
        import copy

        test_config = copy.deepcopy(mock_config)
        test_config["simulation"]["tile_size_meters"] = 1
        test_config["performance"]["spatial_hash_cell_size"] = 10
        return EntityManager(config_data=test_config, tile_size=1)

    def test_find_closest_entity_in_radius_with_predicate(self, manager_for_find_test):
        manager = manager_for_find_test
        origin = np.array([50.0, 50.0])
        unmatured_rice = manager.create_entity("rice", pos_y=5, pos_x=5)
        unmatured_rice.position = np.array([55.0, 55.0])
        unmatured_rice.age = 1
        matured_rice = manager.create_entity("rice", pos_y=8, pos_x=8)
        matured_rice.position = np.array([80.0, 80.0])
        matured_rice.age = matured_rice.mature_age
        is_mature_predicate = lambda r: r.matured
        found_entity = manager.find_closest_entity_in_radius(
            origin_pos_yx=origin,
            entity_type_class=Rice,
            search_radius=100.0,
            predicate=is_mature_predicate,
        )
        assert found_entity is not None, "A valid entity should have been found."
        assert (
            found_entity.id == matured_rice.id
        ), "Should find the farther, but mature, rice."

    def test_find_closest_entity_in_radius_calls_correct_spatial_hash(
        self, entity_manager
    ):
        manager = entity_manager
        origin_pos = np.array([50.0, 50.0])
        search_radius = 100.0
        with patch.object(
            manager.spatial_hashes["rice"], "find_closest_in_radius", autospec=True
        ) as mock_find:
            mock_find.return_value = "fake_rice_entity"
            result = manager.find_closest_entity_in_radius(
                origin_pos_yx=origin_pos,
                entity_type_class=Rice,
                search_radius=search_radius,
            )
            mock_find.assert_called_once_with(origin_pos, search_radius)
            assert result == "fake_rice_entity"


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
    if "sheep" not in mock_config["entities"]:
        mock_config["entities"]["sheep"] = {
            "attributes": {
                "max_age": 1,
                "move_speed": 1,
                "max_saturation": 1,
                "hungry_threshold": 1,
                "reproduction_threshold": 1,
                "reproduction_cost": 1,
                "reproduction_cooldown": 1,
                "newborn_saturation_endowment": 1,
                "search_radius": 1,
            }
        }
    tile_size = mock_config["simulation"]["tile_size_meters"]
    manager = EntityManager(config_data=mock_config, tile_size=tile_size)
    sheep = manager.create_entity("sheep", pos_y=10, pos_x=12)
    assert "sheep" in manager.entity_pools
    assert "sheep" in manager.spatial_hashes
    assert isinstance(sheep, Sheep)
    assert len(manager.entities) == 1
    assert manager.entities[0] is sheep
    assert sheep.position[0] == 105.0
    assert sheep.position[1] == 125.0
