# tests/test_sheep_logic.py
import pytest
import numpy as np
from unittest.mock import MagicMock
from domain.rice import Rice
from domain.sheep import Sheep


# --- Mocks and Fixtures ---
class MockWorld:
    def __init__(self):
        self.width = 100
        self.height = 100
        self.tile_size_meters = 1
        self.entity_manager = MagicMock()
        self.entity_manager.find_nearest_entity_in_vicinity = MagicMock()
        self.entity_manager.find_closest_entity_in_radius = MagicMock()

        self.grid = [
            [
                type("MockTile", (), {"tile_move_speed_factor": 1.0})()
                for _ in range(self.width)
            ]
            for _ in range(self.height)
        ]

    def find_path(self, start_pos_yx, end_pos_yx):
        return (
            [(start_pos_yx[0] + 1, start_pos_yx[1] + 1)]
            if not np.array_equal(start_pos_yx, end_pos_yx)
            else []
        )

    def get_tile_at_pos(self, pos_y: float, pos_x: float):
        grid_y = int(pos_y)
        grid_x = int(pos_x)
        return self.grid[grid_y][grid_x]

    def get_grid_position(self, world_position_yx: np.ndarray) -> tuple[int, int]:
        grid_y = int(world_position_yx[0] / self.tile_size_meters)
        grid_x = int(world_position_yx[1] / self.tile_size_meters)
        return (grid_y, grid_x)


@pytest.fixture
def sheep_config():
    """Provides a sample configuration for a Sheep entity."""
    return {
        "max_age": 1600,
        "move_speed": 0.5,
        "max_saturation": 80,
        "hungry_threshold": 40,
        "reproduction_threshold": 60,
        "reproduction_cost": 15,
        "reproduction_cooldown": 400,
        "newborn_saturation_endowment": 15,
        "search_radius": 100.0,
    }


@pytest.fixture
def sheep(sheep_config):
    """Creates a Sheep instance for testing."""
    return Sheep(pos_y=50, pos_x=50, **sheep_config)


@pytest.fixture
def mock_world():
    """Provides a mock world for tests."""
    return MockWorld()


@pytest.fixture
def rice_config():
    """Provides a sample configuration for a Rice entity."""
    return {"max_age": 100, "mature_age": 50, "saturation_yield": 30}


@pytest.fixture
def rice_plant(rice_config):
    """Creates a Rice instance for testing."""
    return Rice(pos_y=51, pos_x=51, **rice_config)


class TestSheepInternalState:
    def test_sheep_initializes_with_full_saturation(self, sheep):
        assert sheep.saturation == 80

    def test_sheep_loses_saturation_each_tick(self, sheep, mock_world):
        initial_saturation = sheep.saturation
        sheep.tick(mock_world)
        assert sheep.saturation == initial_saturation - 1


class TestSheepAI:
    def test_not_hungry_sheep_wanders_using_path(self, sheep, mock_world, sheep_config):
        sheep.saturation = sheep_config["max_saturation"]
        initial_pos = sheep.position.copy()
        assert not sheep.path
        sheep.tick(mock_world)
        assert sheep.path
        assert not np.array_equal(sheep.position, initial_pos)

    def test_hungry_sheep_finds_distant_food_with_radius_search(
        self, sheep, rice_plant, mock_world, sheep_config
    ):
        sheep.saturation = sheep_config["hungry_threshold"] - 1
        sheep.position = np.array([10.0, 10.0])
        initial_pos = sheep.position.copy()
        rice_plant.position = np.array([80.0, 80.0])
        rice_plant.age = rice_plant.mature_age
        mock_world.entity_manager.find_closest_entity_in_radius.return_value = (
            rice_plant
        )
        sheep.tick(mock_world)
        mock_world.entity_manager.find_closest_entity_in_radius.assert_called_once()
        assert sheep.path is not None
        assert len(sheep.path) > 0
        assert not np.array_equal(sheep.position, initial_pos)
        assert not rice_plant.is_eaten

    def test_hungry_sheep_eats_adjacent_mature_rice(
        self, sheep, rice_plant, mock_world, sheep_config
    ):
        sheep.saturation = sheep_config["hungry_threshold"] - 1
        initial_saturation = sheep.saturation
        sheep.position = np.array([51.0, 50.5])
        rice_plant.position = np.array([51.0, 51.0])
        rice_plant.age = rice_plant.mature_age
        mock_world.entity_manager.find_closest_entity_in_radius.return_value = (
            rice_plant
        )
        sheep.tick(mock_world)
        assert sheep.saturation > initial_saturation
        assert rice_plant.is_eaten is True
        mock_world.entity_manager.find_closest_entity_in_radius.assert_called_once()

    def test_hungry_sheep_moves_towards_faraway_rice(
        self, sheep, rice_plant, mock_world, sheep_config
    ):
        sheep.saturation = sheep_config["hungry_threshold"] - 1
        sheep.position = np.array([10.0, 10.0])
        initial_pos = sheep.position.copy()
        rice_plant.position = np.array([51.0, 51.0])
        rice_plant.age = rice_plant.mature_age
        mock_world.entity_manager.find_closest_entity_in_radius.return_value = (
            rice_plant
        )
        sheep.tick(mock_world)
        assert sheep.path is not None
        assert len(sheep.path) > 0
        assert not np.array_equal(sheep.position, initial_pos)
        assert not rice_plant.is_eaten

    def test_hungry_sheep_ignores_immature_rice(
        self, sheep, rice_plant, mock_world, sheep_config
    ):
        sheep.saturation = sheep_config["hungry_threshold"] - 1
        initial_saturation = sheep.saturation
        sheep.position = np.array([51.0, 50.5])
        rice_plant.position = np.array([51.0, 51.0])
        rice_plant.age = rice_plant.mature_age - 1
        mock_world.entity_manager.find_closest_entity_in_radius.return_value = None
        sheep.tick(mock_world)
        assert sheep.saturation == initial_saturation - 1
        assert not rice_plant.is_eaten
        assert sheep.path is not None


class TestSheepReproduction:
    def test_can_reproduce_is_true_when_conditions_are_met(self, sheep, sheep_config):
        sheep.saturation = sheep_config["reproduction_threshold"]
        sheep.reproduction_cooldown = 0
        assert sheep.can_reproduce() is True

    def test_can_reproduce_is_false_if_saturation_is_too_low(self, sheep, sheep_config):
        sheep.saturation = sheep_config["reproduction_threshold"] - 1
        sheep.reproduction_cooldown = 0
        assert sheep.can_reproduce() is False

    def test_can_reproduce_is_false_if_on_cooldown(self, sheep, sheep_config):
        sheep.saturation = sheep_config["reproduction_threshold"]
        sheep.reproduction_cooldown = 1
        assert sheep.can_reproduce() is False

    def test_reproduce_method_deducts_saturation_and_sets_cooldown(
        self, sheep, sheep_config
    ):
        sheep.saturation = sheep_config["reproduction_threshold"] + 10
        sheep.reproduction_cooldown = 0
        initial_saturation = sheep.saturation
        newborn_saturation = sheep.reproduce()
        assert (
            sheep.saturation == initial_saturation - sheep_config["reproduction_cost"]
        )
        # --- THIS IS THE FIX ---
        # The config key is "reproduction_cooldown", not "reproduction_cooldown_max"
        assert sheep.reproduction_cooldown == sheep_config["reproduction_cooldown"]
        assert newborn_saturation == sheep_config["newborn_saturation_endowment"]
