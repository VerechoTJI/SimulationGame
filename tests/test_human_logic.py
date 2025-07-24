# test/test_human_logic.py
import pytest
import numpy as np
from unittest.mock import MagicMock

from domain.human import Human
from domain.rice import Rice
from domain.entity import Entity


# --- Mocks and Fixtures (Unchanged) ---
class MockEntityManager:
    def __init__(self):
        self.entities = []
        self.find_nearest_entity_in_vicinity = MagicMock()


class MockWorld:
    def __init__(self, config):
        self.config = config
        sim_config = config["simulation"]
        self.width = sim_config["grid_width"]
        self.height = sim_config["grid_height"]
        self.tile_size_meters = sim_config["tile_size_meters"]
        self.grid = [
            [
                type("MockTile", (), {"tile_move_speed_factor": 1.0})()
                for _ in range(self.width)
            ]
            for _ in range(self.height)
        ]
        self.logs = []
        self.entity_manager = MockEntityManager()
        self.food_flow_field = np.zeros((self.height, self.width, 2), dtype=np.int8)

    def add_log(self, message):
        self.logs.append(message)

    def get_tile_at_pos(self, pos_y: float, pos_x: float):
        grid_y = np.clip(int(pos_y / self.tile_size_meters), 0, self.height - 1)
        grid_x = np.clip(int(pos_x / self.tile_size_meters), 0, self.width - 1)
        return self.grid[grid_y][grid_x]

    def get_grid_position(self, world_position_yx: np.ndarray) -> tuple[int, int]:
        grid_y = int(world_position_yx[0] / self.tile_size_meters)
        grid_x = int(world_position_yx[1] / self.tile_size_meters)
        return (grid_y, grid_x)

    def find_path(self, start_pos_yx, end_pos_yx):
        return [(1, 1), (2, 2)] if start_pos_yx != end_pos_yx else []

    def get_flow_vector_at_position(self, world_position_yx: np.ndarray) -> np.ndarray:
        grid_y, grid_x = self.get_grid_position(world_position_yx)
        return self.food_flow_field[grid_y, grid_x]


@pytest.fixture
def human_config():
    return {
        "max_age": 100,
        "move_speed": 1,
        "max_saturation": 100,
        "hungry_threshold": 40,
        "reproduction_threshold": 90,
        "reproduction_cost": 50,
        "reproduction_cooldown": 20,
        "newborn_saturation_endowment": 40,
    }


@pytest.fixture
def rice_config():
    return {"max_age": 50, "mature_age": 25, "saturation_yield": 60}


@pytest.fixture
def human(human_config):
    return Human(pos_y=50, pos_x=50, **human_config)


@pytest.fixture
def rice_plant(rice_config):
    return Rice(pos_y=51, pos_x=51, **rice_config)


@pytest.fixture
def mock_world_with_entities(mock_config):
    return MockWorld(mock_config)


# --- Test Classes ---
class TestHumanInternalState:
    def test_human_initializes_with_full_saturation(self, human):
        assert human.saturation == 100

    def test_human_loses_saturation_each_tick(self, human, mock_world_with_entities):
        # ARRANGE
        initial_saturation = human.saturation
        # --- FIX: Explicitly mock the dependency for this test case ---
        mock_world_with_entities.entity_manager.find_nearest_entity_in_vicinity.return_value = (
            None
        )

        # ACT
        human.tick(mock_world_with_entities)

        # ASSERT
        assert human.saturation == initial_saturation - 1

    def test_eating_replenishes_saturation_and_marks_rice_as_eaten(
        self, human, rice_plant
    ):
        human.saturation = 10
        initial_saturation = human.saturation
        assert rice_plant.is_eaten is False
        human.eat(rice_plant)
        assert human.saturation == initial_saturation + rice_plant.saturation_yield
        assert rice_plant.is_eaten is True


class TestHumanAI:
    def test_hungry_human_moves_along_flow_field(self, human, mock_world_with_entities):
        human.saturation = 30
        human.position = np.array([55.0, 55.0])
        initial_pos = human.position.copy()
        mock_world_with_entities.entity_manager.find_nearest_entity_in_vicinity.return_value = (
            None
        )
        grid_y, grid_x = mock_world_with_entities.get_grid_position(human.position)
        mock_world_with_entities.food_flow_field[grid_y, grid_x] = np.array([1, 1])
        human.tick(mock_world_with_entities)
        assert not human.path
        assert human.position[0] > initial_pos[0]
        assert human.position[1] > initial_pos[1]

    def test_not_hungry_human_wanders_using_path(self, human, mock_world_with_entities):
        human.saturation = 80
        assert not human.path
        mock_world_with_entities.entity_manager.find_nearest_entity_in_vicinity.return_value = (
            None
        )
        human.tick(mock_world_with_entities)
        assert human.path
        assert human.path == [(1, 1), (2, 2)]

    def test_becoming_hungry_clears_wandering_path(
        self, human, mock_world_with_entities
    ):
        human.saturation = 80
        human.position = np.array([55.0, 55.0])
        mock_world_with_entities.entity_manager.find_nearest_entity_in_vicinity.return_value = (
            None
        )
        human.tick(mock_world_with_entities)
        assert human.path
        grid_y, grid_x = mock_world_with_entities.get_grid_position(human.position)
        mock_world_with_entities.food_flow_field[grid_y, grid_x] = np.array([1, 0])
        human.saturation = 30
        human.tick(mock_world_with_entities)
        assert not human.path

    def test_human_eats_when_next_to_food(
        self, human, mock_world_with_entities, rice_plant
    ):
        human.saturation = 20
        human.position = np.array([55.0, 55.0])
        rice_plant.position = np.array([56.0, 56.0])
        rice_plant.age = rice_plant.mature_age
        mock_world_with_entities.entity_manager.find_nearest_entity_in_vicinity.return_value = (
            rice_plant
        )
        initial_saturation = human.saturation
        human.tick(mock_world_with_entities)
        mock_world_with_entities.entity_manager.find_nearest_entity_in_vicinity.assert_called_once()
        assert human.saturation > initial_saturation
        assert rice_plant.is_eaten is True

    def test_human_does_not_eat_if_food_is_too_far(
        self, human, mock_world_with_entities, rice_plant
    ):
        human.saturation = 20
        human.position = np.array([55.0, 55.0])
        rice_plant.position = np.array([80.0, 80.0])
        rice_plant.age = rice_plant.mature_age
        mock_world_with_entities.entity_manager.find_nearest_entity_in_vicinity.return_value = (
            rice_plant
        )
        initial_saturation = human.saturation
        human.tick(mock_world_with_entities)
        assert human.saturation == initial_saturation - 1
        assert rice_plant.is_eaten is False


class TestHumanReproduction:
    def test_can_reproduce_is_true_when_conditions_are_met(self, human):
        human.saturation = 95
        human.reproduction_cooldown = 0
        assert human.can_reproduce() is True

    def test_can_reproduce_is_false_if_saturation_is_too_low(self, human):
        human.saturation = 80
        human.reproduction_cooldown = 0
        assert human.can_reproduce() is False

    def test_can_reproduce_is_false_if_on_cooldown(self, human):
        human.saturation = 95
        human.reproduction_cooldown = 10
        assert human.can_reproduce() is False

    def test_reproduce_method_deducts_saturation_and_sets_cooldown(
        self, human, human_config
    ):
        human.saturation = 98
        human.reproduction_cooldown = 0
        newborn_saturation = human.reproduce()
        assert human.saturation == 98 - human_config["reproduction_cost"]
        assert human.reproduction_cooldown == human_config["reproduction_cooldown"]
        assert newborn_saturation == human_config["newborn_saturation_endowment"]
