# test/test_sheep_logic.py
import pytest
import numpy as np
from unittest.mock import MagicMock
from domain.rice import Rice

# We will create this file in the next step
# from domain.sheep import Sheep


# --- Mocks and Fixtures ---
# A simplified mock world is sufficient for unit testing the Sheep in isolation.
class MockWorld:
    def __init__(self):
        self.width = 100
        self.height = 100
        self.tile_size_meters = 1
        self.entity_manager = MagicMock()
        self.entity_manager.find_nearest_entity_in_vicinity = MagicMock()
        # Add a mock grid to check for passable tiles
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
            if start_pos_yx != end_pos_yx
            else []
        )

    def get_tile_at_pos(self, pos_y: float, pos_x: float):
        # The logic here can be simplified for the mock.
        # We assume coordinates are within bounds for testing purposes.
        grid_y = int(pos_y)
        grid_x = int(pos_x)
        return self.grid[grid_y][grid_x]

    # --- THIS IS THE FIX ---
    def get_grid_position(self, world_position_yx: np.ndarray) -> tuple[int, int]:
        """Converts world coordinates to grid coordinates."""
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
    }


@pytest.fixture
def sheep(sheep_config):
    """Creates a Sheep instance for testing."""
    # This import will fail until we create the Sheep class
    from domain.sheep import Sheep

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


# --- Test Classes ---


class TestSheepInternalState:
    def test_sheep_initializes_with_full_saturation(self, sheep):
        """
        Tests that a newly created sheep starts with its saturation at the maximum value.
        """
        assert sheep.saturation == 80

    def test_sheep_loses_saturation_each_tick(self, sheep, mock_world):
        """
        Tests that a sheep's saturation decreases by 1 after a single tick.
        """
        # ARRANGE
        initial_saturation = sheep.saturation
        # Act on the sheep
        sheep.tick(mock_world)

        # ASSERT
        assert sheep.saturation == initial_saturation - 1


class TestSheepAI:
    def test_not_hungry_sheep_wanders_using_path(self, sheep, mock_world, sheep_config):
        """
        Tests that a sheep with high saturation will generate a path and start moving.
        """
        # ARRANGE
        sheep.saturation = sheep_config["max_saturation"]
        initial_pos = sheep.position.copy()
        assert not sheep.path

        # ACT
        sheep.tick(mock_world)

        # ASSERT
        # Assert that the world's pathfinder was called to generate a path.
        # The mock_world's find_path returns a pre-defined path.
        assert sheep.path
        # Assert the sheep has moved from its starting position.
        assert not np.array_equal(sheep.position, initial_pos)

    def test_hungry_sheep_eats_adjacent_mature_rice(
        self, sheep, rice_plant, mock_world, sheep_config
    ):
        """
        Tests that a hungry sheep eats a mature rice plant it is next to.
        """
        # ARRANGE
        sheep.saturation = sheep_config["hungry_threshold"] - 1
        initial_saturation = sheep.saturation

        # Place sheep right next to the rice
        sheep.position = np.array([51.0, 50.5])
        rice_plant.position = np.array([51.0, 51.0])
        rice_plant.age = rice_plant.mature_age  # Make sure rice is mature

        # Mock the entity manager to return this specific rice plant
        mock_world.entity_manager.find_nearest_entity_in_vicinity.return_value = (
            rice_plant
        )

        # ACT
        sheep.tick(mock_world)

        # ASSERT
        assert sheep.saturation > initial_saturation
        assert rice_plant.is_eaten is True
        # The entity manager's find method should have been called
        mock_world.entity_manager.find_nearest_entity_in_vicinity.assert_called_once()

    def test_hungry_sheep_moves_towards_faraway_rice(
        self, sheep, rice_plant, mock_world, sheep_config
    ):
        """
        Tests that a hungry sheep will generate a path to faraway food and move.
        """
        # ARRANGE
        sheep.saturation = sheep_config["hungry_threshold"] - 1
        sheep.position = np.array([10.0, 10.0])
        initial_pos = sheep.position.copy()

        rice_plant.position = np.array([51.0, 51.0])
        rice_plant.age = rice_plant.mature_age

        mock_world.entity_manager.find_nearest_entity_in_vicinity.return_value = (
            rice_plant
        )

        # ACT
        sheep.tick(mock_world)

        # ASSERT
        assert sheep.path is not None
        assert len(sheep.path) > 0
        assert not np.array_equal(sheep.position, initial_pos)  # It should have moved
        assert rice_plant.is_eaten is False  # It's too far to eat

    def test_hungry_sheep_ignores_immature_rice(
        self, sheep, rice_plant, mock_world, sheep_config
    ):
        """
        Tests that a hungry sheep will not eat or path to immature rice.
        """
        # ARRANGE
        sheep.saturation = sheep_config["hungry_threshold"] - 1
        initial_saturation = sheep.saturation

        sheep.position = np.array([51.0, 50.5])
        rice_plant.position = np.array([51.0, 51.0])
        rice_plant.age = rice_plant.mature_age - 1  # Make rice immature

        # The predicate in the sheep's find call should filter this out
        mock_world.entity_manager.find_nearest_entity_in_vicinity.return_value = None

        # ACT
        sheep.tick(mock_world)

        # ASSERT
        # Saturation should decrease because it didn't eat
        assert sheep.saturation == initial_saturation - 1
        assert rice_plant.is_eaten is False
        # It should have wandered instead, so it should have a path
        assert sheep.path is not None
        assert len(sheep.path) > 0


class TestSheepReproduction:
    def test_can_reproduce_is_true_when_conditions_are_met(self, sheep, sheep_config):
        """
        Tests that can_reproduce() returns True when saturation is high and cooldown is off.
        """
        # ARRANGE
        sheep.saturation = sheep_config["reproduction_threshold"]
        sheep.reproduction_cooldown = 0

        # ASSERT
        assert sheep.can_reproduce() is True

    def test_can_reproduce_is_false_if_saturation_is_too_low(self, sheep, sheep_config):
        """
        Tests that can_reproduce() is False when saturation is below the threshold.
        """
        # ARRANGE
        sheep.saturation = sheep_config["reproduction_threshold"] - 1
        sheep.reproduction_cooldown = 0

        # ASSERT
        assert sheep.can_reproduce() is False

    def test_can_reproduce_is_false_if_on_cooldown(self, sheep, sheep_config):
        """
        Tests that can_reproduce() is False when the cooldown is active.
        """
        # ARRANGE
        sheep.saturation = sheep_config["reproduction_threshold"]
        sheep.reproduction_cooldown = 1

        # ASSERT
        assert sheep.can_reproduce() is False

    def test_reproduce_method_deducts_saturation_and_sets_cooldown(
        self, sheep, sheep_config
    ):
        """
        Tests that reproduce() correctly updates parent's state and returns newborn saturation.
        """
        # ARRANGE
        sheep.saturation = sheep_config["reproduction_threshold"] + 10
        sheep.reproduction_cooldown = 0
        initial_saturation = sheep.saturation

        # ACT
        newborn_saturation = sheep.reproduce()

        # ASSERT
        assert (
            sheep.saturation == initial_saturation - sheep_config["reproduction_cost"]
        )
        assert sheep.reproduction_cooldown == sheep_config["reproduction_cooldown"]
        assert newborn_saturation == sheep_config["newborn_saturation_endowment"]
