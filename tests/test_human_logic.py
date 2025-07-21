# tests/test_human_logic.py
import pytest
import numpy as np

from domain.human import Human
from domain.rice import Rice


# --- A mock EntityManager to be used by MockWorld ---
class MockEntityManager:
    def __init__(self):
        self.entities = []

    def find_nearest_entity(self, origin_pos, entity_type, predicate=None):
        closest_entity = None
        min_dist_sq = float("inf")
        for entity in self.entities:
            if isinstance(entity, entity_type) and (not predicate or predicate(entity)):
                dist_sq = np.sum((entity.position - origin_pos) ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq, closest_entity = dist_sq, entity
        return closest_entity


# --- REFACTORED MockWorld ---
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
        # --- FIX: MockWorld now has a mock entity_manager ---
        self.entity_manager = MockEntityManager()

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
        return [end_pos] if start_pos != end_pos else []


@pytest.fixture
def mock_world_with_entities(mock_config):
    """Provides a clean mock world that can hold entities."""
    return MockWorld(mock_config)


class TestHumanInternalState:
    def test_human_initializes_with_full_saturation(self, human):
        assert human.saturation == 100

    def test_human_loses_saturation_each_tick(self, human, mock_world_with_entities):
        initial_saturation = human.saturation
        # --- FIX: The human's tick() logic now accesses world.entity_manager ---
        # No change to the test code itself is needed, but the mock now supports it.
        human.tick(mock_world_with_entities)
        assert human.saturation == initial_saturation - 1

    def test_eating_replenishes_saturation_and_marks_rice_as_eaten(
        self, human, rice_plant
    ):
        rice_plant.age = rice_plant.max_age
        human.saturation = 10
        initial_saturation = human.saturation
        assert rice_plant.is_eaten is False
        human.eat(rice_plant)
        assert human.saturation == initial_saturation + rice_plant.saturation_yield
        assert rice_plant.is_eaten is True


class TestHumanAI:
    def test_hungry_human_finds_path_to_food(
        self, human, mock_world_with_entities, rice_config
    ):
        human.saturation = 30
        human.path = []
        food = Rice(pos_x=85, pos_y=85, **rice_config)
        food.age = food.max_age
        # --- FIX: Add the food entity to the mock entity_manager ---
        mock_world_with_entities.entity_manager.entities.append(food)

        human.tick(mock_world_with_entities)
        assert human.path and human.path[-1] == (8, 8)

    def test_human_eats_when_next_to_food(
        self, human, mock_world_with_entities, rice_config
    ):
        human.saturation = 20
        human.position = np.array([55.0, 55.0])
        food = Rice(**rice_config, pos_x=56, pos_y=56)
        food.age = food.max_age
        # --- FIX: Add the food entity to the mock entity_manager ---
        mock_world_with_entities.entity_manager.entities.append(food)

        assert food.is_eaten is False
        initial_saturation = human.saturation

        human.tick(mock_world_with_entities)

        assert human.saturation > initial_saturation
        assert food.is_eaten is True
        assert not human.path


class TestHumanReproduction:
    # This whole class is unchanged as it only tests internal Human logic
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
