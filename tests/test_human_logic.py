import pytest
import numpy as np

from domain.human import Human
from domain.rice import Rice


# --- A mock EntityManager to be used by MockWorld ---
class MockEntityManager:
    def __init__(self):
        self.entities = []

    # This method is no longer directly used by the Human's main logic but is
    # kept for other potential tests or if the eating logic gets more complex.
    def find_nearest_entity(self, origin_pos, entity_type, predicate=None):
        closest_entity = None
        min_dist_sq = float("inf")
        for entity in self.entities:
            if isinstance(entity, entity_type) and (not predicate or predicate(entity)):
                dist_sq = np.sum((entity.position - origin_pos) ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq, closest_entity = dist_sq, entity
        return closest_entity


# --- REFACTORED MockWorld with Flow Field Support ---
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

        # --- NEW: Add mock flow field support ---
        self.food_flow_field = np.zeros((self.height, self.width, 2), dtype=np.int8)

    def add_log(self, message):
        self.logs.append(message)

    def get_tile_at_pos(self, pos_x, pos_y):
        grid_x = np.clip(int(pos_x / self.tile_size_meters), 0, self.width - 1)
        grid_y = np.clip(int(pos_y / self.tile_size_meters), 0, self.height - 1)
        return self.grid[grid_y][grid_x]

    def get_grid_position(self, world_position):
        grid_x = int(world_position[0] / self.tile_size_meters)
        grid_y = int(world_position[1] / self.tile_size_meters)
        return (grid_x, grid_y)

    def find_path(self, start_pos, end_pos):
        # Return a predictable path for testing wandering
        return [(1, 1), (2, 2)] if start_pos != end_pos else []

    # --- NEW: Mock method for Human to call ---
    def get_flow_vector_at_position(self, world_position):
        grid_x, grid_y = self.get_grid_position(world_position)
        return self.food_flow_field[grid_y, grid_x]


@pytest.fixture
def mock_world_with_entities(mock_config):
    """Provides a clean mock world that can hold entities."""
    return MockWorld(mock_config)


class TestHumanInternalState:
    # This class remains unchanged as it tests core attributes
    def test_human_initializes_with_full_saturation(self, human):
        assert human.saturation == 100

    def test_human_loses_saturation_each_tick(self, human, mock_world_with_entities):
        initial_saturation = human.saturation
        human.tick(mock_world_with_entities)
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
        # ARRANGE
        human.saturation = 30  # Make hungry
        human.position = np.array([55.0, 55.0])  # Grid pos (5, 5)
        initial_pos = human.position.copy()

        # Set a flow vector pointing South-East (dy=1, dx=1) at the human's location
        mock_world_with_entities.food_flow_field[5, 5] = np.array([1, 1])

        # ACT
        human.tick(mock_world_with_entities)

        # ASSERT
        assert not human.path, "A hungry human should not generate an A* path"
        assert (
            human.position[0] > initial_pos[0]
        ), "Human should have moved in positive X direction"
        assert (
            human.position[1] > initial_pos[1]
        ), "Human should have moved in positive Y direction"

    def test_not_hungry_human_wanders_using_path(self, human, mock_world_with_entities):
        # ARRANGE
        human.saturation = 80  # Not hungry
        assert not human.path

        # ACT
        human.tick(mock_world_with_entities)

        # ASSERT
        assert human.path, "A sated human should generate a path to wander"
        # Check against the predictable path from our mock find_path
        assert human.path == [(1, 1), (2, 2)]

    def test_becoming_hungry_clears_wandering_path(
        self, human, mock_world_with_entities
    ):
        # ARRANGE
        human.saturation = 80  # Not hungry
        human.position = np.array([55.0, 55.0])  # Grid pos (5, 5)
        human.tick(mock_world_with_entities)  # Generates a wandering path
        assert human.path, "Pre-condition: Human must have a wandering path"

        # --- IMPROVEMENT: Simulate that food now exists by setting a flow vector ---
        # This ensures the test is valid even when the flow isn't zero.
        mock_world_with_entities.food_flow_field[5, 5] = np.array([1, 0])  # Point South

        # ACT
        human.saturation = 30  # Becomes hungry
        human.tick(mock_world_with_entities)  # Tick again

        # ASSERT
        assert not human.path, "Becoming hungry should clear any existing path"

    def test_human_eats_when_next_to_food(
        self, human, mock_world_with_entities, rice_config
    ):
        # This test remains valid as eating is checked before movement.
        human.saturation = 20
        human.position = np.array([55.0, 55.0])
        food = Rice(**rice_config, pos_x=56, pos_y=56)
        food.age = food.max_age
        mock_world_with_entities.entity_manager.entities.append(food)

        assert food.is_eaten is False
        initial_saturation = human.saturation

        human.tick(mock_world_with_entities)

        assert human.saturation > initial_saturation
        assert food.is_eaten is True
        assert not human.path


# TestHumanReproduction class remains unchanged
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

    def test_reproduce_method_deducts_saturation_and_sets_cooldown(self, human):
        human.saturation = 98
        human.reproduction_cooldown = 0
        newborn_saturation = human.reproduce()
        assert human.saturation == 48
        assert human.reproduction_cooldown == 20
        assert newborn_saturation == 40
