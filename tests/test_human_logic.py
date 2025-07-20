# tests/test_human_logic.py
import pytest
import numpy as np

from domain.human import Human
from domain.rice import Rice


# --- Let's define a more robust MockWorld that accepts a config ---
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
        self.entities = []
        self.logs = []

    def get_config_value(self, *keys, default=None):
        value = self.config
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def add_log(self, message):
        self.logs.append(message)

    def get_tile_at_pos(self, pos_x, pos_y):
        grid_x = np.clip(int(pos_x / self.tile_size_meters), 0, self.width - 1)
        grid_y = np.clip(int(pos_y / self.tile_size_meters), 0, self.height - 1)
        return self.grid[grid_y][grid_x]

    def find_path(self, start_pos, end_pos):
        return [end_pos] if start_pos != end_pos else []

    def find_nearest_entity(self, origin_pos, entity_type, predicate=None):
        # ... (implementation from before)
        closest_entity = None
        min_dist_sq = float("inf")
        for entity in self.entities:
            if isinstance(entity, entity_type) and (not predicate or predicate(entity)):
                dist_sq = np.sum((entity.position - origin_pos) ** 2)
                if dist_sq < min_dist_sq:
                    min_dist_sq, closest_entity = dist_sq, entity
        return closest_entity


@pytest.fixture
def mock_world_with_entities(mock_config):  # Now uses the central mock_config
    """Provides a clean mock world that can hold entities."""
    return MockWorld(mock_config)


# The 'human' fixture from conftest.py is already available.


class TestHumanInternalState:
    # --- MODIFIED: All tests now use the fixtures from conftest ---
    def test_human_initializes_with_full_saturation(self, human):
        assert human.saturation == 100
        assert human.max_saturation == 100

    def test_human_loses_saturation_each_tick(self, human, mock_world_with_entities):
        initial_saturation = human.saturation
        human.tick(mock_world_with_entities)
        assert human.saturation == initial_saturation - 1

    # ... other internal state tests are fine as they just use the 'human' fixture.

    def test_eating_replenishes_saturation_and_replants_rice(self, human, rice_plant):
        rice_plant.age = rice_plant.max_age
        human.saturation = 10
        initial_saturation = human.saturation

        human.eat(rice_plant)  # Just pass the plant itself

        # The expected gain now comes from the rice_plant fixture's config
        assert human.saturation == initial_saturation + rice_plant.saturation_yield
        assert rice_plant.age == 0


class TestHumanAI:
    # --- MODIFIED: Needs to instantiate Rice with config ---
    def test_hungry_human_finds_path_to_food(
        self, human, mock_world_with_entities, rice_config
    ):
        human.saturation = 30
        human.path = []

        food = Rice(
            pos_x=85,
            pos_y=85,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )
        food.age = food.max_age
        mock_world_with_entities.entities.append(food)

        human.tick(mock_world_with_entities)
        assert human.path and human.path[-1] == (8, 8)

    def test_human_eats_when_next_to_food(
        self, human, mock_world_with_entities, rice_config
    ):
        # ... similar change to instantiate Rice with config
        human.saturation = 20
        human.position = np.array([55.0, 55.0])
        food = Rice(
            pos_x=56,
            pos_y=56,
            max_age=rice_config["max_age"],
            saturation_yield=rice_config["saturation_yield"],
        )
        food.age = food.max_age
        mock_world_with_entities.entities.append(food)

        initial_saturation = human.saturation
        human.tick(mock_world_with_entities)

        assert human.saturation > initial_saturation
        assert food.age == 0
        assert not human.path
