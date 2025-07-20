# tests/test_world_spawning.py
import pytest
from unittest.mock import patch

from domain.rice import Rice
from domain.human import Human
from domain.world import TILES


# The 'world_with_fixed_map' fixture is now global.
# We just need to add the fixed grid data inside the test.
from domain.world import TILES


@pytest.fixture
def spawning_world(world_factory):
    """Creates a 5x5 world with a predictable map for spawning tests."""
    world = world_factory(width=5, height=5)

    # Define the grid layout
    fixed_grid = [
        [TILES["water"]] * 5,
        [TILES["water"], TILES["land"], TILES["land"], TILES["land"], TILES["water"]],
        [
            TILES["water"],
            TILES["land"],
            TILES["mountain"],
            TILES["land"],
            TILES["water"],
        ],
        [TILES["water"], TILES["land"], TILES["land"], TILES["land"], TILES["water"]],
        [TILES["water"]] * 5,
    ]
    # Set the grid on the correctly-sized world object
    world.grid = fixed_grid
    return world


class TestNaturalSpawning:
    def test_rice_spawns_on_valid_tile(self, spawning_world):
        world = spawning_world
        assert len(world.entities) == 0

        with patch("random.random", return_value=0.0):
            world.natural_spawning_tick()

        assert len(world.entities) == 1
        new_entity = world.entities[0]
        assert isinstance(new_entity, Rice)

        entity_grid_pos = (
            int(new_entity.position[0] / world.tile_size_meters),
            int(new_entity.position[1] / world.tile_size_meters),
        )
        valid_spawn_points = {
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 3),
            (2, 3),
            (3, 3),
            (1, 2),
            (3, 2),
        }
        assert entity_grid_pos in valid_spawn_points

    def test_rice_does_not_spawn_if_chance_fails(self, spawning_world):
        with patch("random.random", return_value=0.99):
            spawning_world.natural_spawning_tick()

        assert len(spawning_world.entities) == 0

    def test_rice_does_not_spawn_on_occupied_tiles(self, spawning_world, human_config):
        world = spawning_world
        valid_spawn_points = [
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 3),
            (2, 3),
            (3, 3),
            (1, 2),
            (3, 2),
        ]
        for x, y in valid_spawn_points:
            pos_x = (x + 0.5) * world.tile_size_meters
            pos_y = (y + 0.5) * world.tile_size_meters
            # Pass the required config arguments to Human
            world.entities.append(Human(pos_x, pos_y, **human_config))

        initial_entity_count = len(world.entities)

        with patch("random.random", return_value=0.0):
            world.natural_spawning_tick()

        assert len(world.entities) == initial_entity_count
