# tests/test_world_spawning.py
import pytest
import random
from unittest.mock import patch

from domain.world import World, TILES
from domain.rice import Rice
from domain.human import Human


@pytest.fixture
def world_with_fixed_map():
    """Creates a world with a predictable map for testing."""
    # We create an instance but will override its grid
    world = World(width=5, height=5, tile_size=10)

    # Grid layout:
    # W W W W W
    # W L L L W
    # W L M L W   (M = Mountain)
    # W L L L W
    # W W W W W

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
    world.grid = fixed_grid
    return world


class TestNaturalSpawning:
    def test_rice_spawns_on_valid_tile(self, world_with_fixed_map):
        """
        GIVEN a world with land next to water,
        WHEN a spawning tick occurs with a 100% chance,
        THEN a new Rice plant should appear on a valid tile.
        """
        # GIVEN
        world = world_with_fixed_map
        assert len(world.entities) == 0

        # We "patch" random.random to always return 0.0, ensuring a spawn happens
        with patch("random.random", return_value=0.0):
            # WHEN
            world.natural_spawning_tick()

        # THEN
        assert len(world.entities) == 1
        new_entity = world.entities[0]
        assert isinstance(new_entity, Rice)

        # Check that it spawned on a valid land tile next to water.
        # Valid coordinates are: (1,1), (1,2), (1,3), (2,1), (2,3), (3,1), (3,2), (3,3)
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

    def test_rice_does_not_spawn_if_chance_fails(self, world_with_fixed_map):
        """
        GIVEN a world with valid spawn points,
        WHEN the random chance is too high (fails),
        THEN no Rice should spawn.
        """
        # We "patch" random.random to always return 0.99, which is higher than the spawn chance
        with patch("random.random", return_value=0.99):
            world_with_fixed_map.natural_spawning_tick()

        assert len(world_with_fixed_map.entities) == 0

    def test_rice_does_not_spawn_on_occupied_tiles(self, world_with_fixed_map):
        """
        GIVEN all valid spawn points are occupied,
        WHEN a spawning tick occurs,
        THEN no new Rice should spawn.
        """
        world = world_with_fixed_map
        # Manually occupy all valid land tiles
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
            world.entities.append(Human(pos_x, pos_y))  # Occupy with Humans

        initial_entity_count = len(world.entities)

        with patch("random.random", return_value=0.0):  # 100% chance
            world.natural_spawning_tick()

        assert len(world.entities) == initial_entity_count
