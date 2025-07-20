# tests/test_human_logic.py
import pytest
import numpy as np

from domain.human import Human
from domain.rice import Rice


# --- MODIFIED: The MockWorld is now more realistic ---
class MockWorld:
    """A mock world that has the attributes the Human tick() method expects."""

    def __init__(self):
        # Attributes needed for movement/pathing logic in Human.tick()
        self.width = 10
        self.height = 10
        self.tile_size_meters = 10
        # A simple grid of passable tiles
        self.grid = [
            [
                type("MockTile", (), {"tile_move_speed_factor": 1.0})()
                for _ in range(self.width)
            ]
            for _ in range(self.height)
        ]

    # --- Methods needed by Human.tick() ---
    def add_log(self, message):
        pass  # We don't need to test logging here

    def get_tile_at_pos(self, pos_x, pos_y):
        # A simple, safe implementation for the mock
        grid_x = np.clip(int(pos_x / self.tile_size_meters), 0, self.width - 1)
        grid_y = np.clip(int(pos_y / self.tile_size_meters), 0, self.height - 1)
        return self.grid[grid_y][grid_x]

    def find_path(self, start_pos, end_pos):
        # For these tests, we don't need a real path.
        # Returning a dummy path prevents crashes in _find_new_path.
        return [end_pos] if start_pos != end_pos else []


@pytest.fixture
def human() -> Human:
    """Provides a brand new Human instance for each test."""
    # Place the human in a valid position within the mock world's bounds
    return Human(pos_x=50, pos_y=50)


@pytest.fixture
def mock_world() -> MockWorld:
    """Provides a clean, functional mock world for each test."""
    return MockWorld()


# The test class and all its test methods remain completely unchanged.
class TestHumanInternalState:
    def test_human_initializes_with_full_saturation(self, human):
        assert human.saturation == 100
        assert human.max_saturation == 100

    def test_human_loses_saturation_each_tick(self, human, mock_world):
        initial_saturation = human.saturation
        human.tick(mock_world)
        assert human.saturation == initial_saturation - 1

    def test_human_is_alive_with_positive_saturation(self, human):
        human.saturation = 1
        assert human.is_alive() is True

    def test_human_dies_from_starvation(self, human):
        human.saturation = 0
        assert human.is_alive() is False

    def test_eating_replenishes_saturation_and_replants_rice(self, human):
        rice = Rice(pos_x=1, pos_y=1)
        rice.age = rice.max_age
        human.saturation = 10
        saturation_gain = 50
        human.eat(rice, saturation_gain)
        assert human.saturation == 10 + saturation_gain
        assert rice.age == 0

    def test_eating_does_not_exceed_max_saturation(self, human):
        rice = Rice(pos_x=1, pos_y=1)
        rice.age = rice.max_age
        human.saturation = 80
        human.eat(rice, saturation_gain=50)
        assert human.saturation == human.max_saturation


class MockWorldWithEntities(MockWorld):
    def __init__(self):
        super().__init__()
        self.entities = []
        self.logs = []  # To check if certain logs are added

    def add_log(self, message):
        self.logs.append(message)

    def find_nearest_entity(self, origin_pos, entity_type, predicate=None):
        """A simple, functional version for testing."""
        closest_entity = None
        min_dist_sq = float("inf")

        for entity in self.entities:
            if isinstance(entity, entity_type):
                if predicate and not predicate(entity):
                    continue

                dist_sq = np.sum((entity.position - origin_pos) ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_entity = entity

        return closest_entity


@pytest.fixture
def mock_world_with_entities() -> MockWorldWithEntities:
    """Provides a clean mock world that can hold entities."""
    return MockWorldWithEntities()


class TestHumanAI:
    def test_hungry_human_finds_path_to_food(self, human, mock_world_with_entities):
        """
        GIVEN a hungry human with no path,
        WHEN the world has a mature rice plant,
        THEN after a tick, the human should have a path towards that rice.
        """
        # GIVEN
        human.saturation = 30  # Make the human hungry
        human.path = []  # Ensure no path exists

        food = Rice(pos_x=85, pos_y=85)  # Place food at grid (8, 8)
        food.age = food.max_age  # Make it mature
        mock_world_with_entities.entities.append(food)

        # WHEN
        human.tick(mock_world_with_entities)

        # THEN
        assert human.path is not None, "Human should have found a path"
        assert len(human.path) > 0, "Path should not be empty"
        # The path should lead to the grid cell of the food
        assert human.path[-1] == (8, 8)

    def test_human_eats_when_next_to_food(self, human, mock_world_with_entities):
        """
        GIVEN a hungry human standing next to food,
        WHEN a tick occurs,
        THEN the human's saturation should increase and the rice should be replanted.
        """
        # GIVEN
        human.saturation = 20
        initial_saturation = human.saturation

        # Place human and food right next to each other
        human.position = np.array([55.0, 55.0])  # Grid (5,5)
        food = Rice(pos_x=56, pos_y=56)  # Also near grid (5,5)
        food.age = food.max_age
        mock_world_with_entities.entities.append(food)

        # WHEN
        human.tick(mock_world_with_entities)

        # THEN
        assert (
            human.saturation > initial_saturation
        ), "Human should have eaten and gained saturation"
        assert food.age == 0, "Rice should have been replanted after being eaten"
        assert not human.path, "Path should be cleared after eating"

    def test_not_hungry_human_wanders_randomly(self, human, mock_world_with_entities):
        """
        GIVEN a not-hungry human,
        WHEN the world has food,
        THEN the human should still choose a random path, not one to the food.
        """
        # GIVEN
        human.saturation = 90  # Not hungry
        human.path = []

        food = Rice(pos_x=85, pos_y=85)  # Grid (8, 8)
        food.age = food.max_age
        mock_world_with_entities.entities.append(food)

        # WHEN
        human.tick(mock_world_with_entities)

        # THEN
        assert human.path is not None
        # It's highly unlikely the random path will end at (8,8).
        # A perfect test might mock random.randint, but for now, this is a strong indicator.
        if human.path:
            assert human.path[-1] != (8, 8)
