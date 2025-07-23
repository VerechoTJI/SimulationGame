# tests/test_spawning_manager.py

import pytest
import random
from domain.spawning_manager import SpawningManager
from domain.entity_manager import EntityManager
from domain.tile import TILES
from domain.rice import Rice

# --- FIXTURES ---


@pytest.fixture
def simple_spawn_grid():
    """A deterministic 3x3 grid for basic spawning rules."""
    return [
        [TILES["land"], TILES["land"], TILES["water"]],
        [TILES["land"], TILES["land"], TILES["water"]],
        [TILES["land"], TILES["land"], TILES["land"]],
    ]


@pytest.fixture
def complex_spawn_grid():
    """A predictable 5x5 grid for more complex natural spawning tests."""
    #      x=0    x=1    x=2    x=3    x=4
    # y=0 [Water, Water, Water, Water, Water],
    # y=1 [Water, Land,  Land,  Land,  Water],
    # y=2 [Water, Land,  Mount, Land,  Water],
    # y=3 [Water, Land,  Land,  Land,  Water],
    # y=4 [Water, Water, Water, Water, Water],
    return [
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


@pytest.fixture
def simple_spawning_manager(simple_spawn_grid, mock_config):
    return SpawningManager(grid=simple_spawn_grid, config_data=mock_config)


@pytest.fixture
def complex_spawning_manager(complex_spawn_grid, mock_config):
    return SpawningManager(grid=complex_spawn_grid, config_data=mock_config)


# --- TEST CLASSES ---


class TestReproductionAndReplanting:
    def test_replant_queue_logic(self, simple_spawning_manager):
        """Tests that the replant queue adds and processes (y, x) coords correctly."""
        assert simple_spawning_manager.process_replant_queue() == []
        simple_spawning_manager.add_to_replant_queue((1, 1))
        simple_spawning_manager.add_to_replant_queue((2, 0))
        assert sorted(simple_spawning_manager.process_replant_queue()) == sorted(
            [(1, 1), (2, 0)]
        )
        assert simple_spawning_manager.process_replant_queue() == []

    def test_reproduction_spawn_location(self, simple_spawning_manager):
        """Tests finding a valid adjacent tile for a newborn using (y, x)."""
        occupied_tiles = {(1, 1)}  # Occupy tile (y=1, x=1)
        # Parent is at (y=0, x=0)
        spawn_pos = simple_spawning_manager.get_reproduction_spawn_location(
            parent_grid_pos_yx=(0, 0), occupied_tiles=occupied_tiles
        )
        assert spawn_pos is not None
        assert spawn_pos in [
            (0, 1),
            (1, 0),
        ]  # Valid spawns are (y=0, x=1) and (y=1, x=0)

    def test_reproduction_spawn_location_fully_blocked(self, simple_spawning_manager):
        """Tests that no location is returned if the parent is surrounded."""
        occupied_tiles = {(1, 0), (0, 1), (1, 1)}  # Occupy all neighbors of (0,0)
        spawn_pos = simple_spawning_manager.get_reproduction_spawn_location(
            parent_grid_pos_yx=(0, 0), occupied_tiles=occupied_tiles
        )
        assert spawn_pos is None


class TestNaturalSpawning:
    def test_rice_spawns_on_valid_tile(self, complex_spawning_manager, monkeypatch):
        monkeypatch.setattr(random, "random", lambda: 0.0)  # Force spawn

        spawn_pos = complex_spawning_manager.get_natural_rice_spawn_location(set())
        assert spawn_pos is not None

        # Valid spawn points are land tiles adjacent to water.
        # See grid layout in fixture for reference.
        valid_spawn_points = {
            (1, 1),
            (1, 2),
            (1, 3),  # Row y=1
            (2, 1),
            (2, 3),  # Row y=2 (excluding mountain)
            (3, 1),
            (3, 2),
            (3, 3),  # Row y=3
        }
        assert spawn_pos in valid_spawn_points

    def test_rice_does_not_spawn_if_chance_fails(
        self, complex_spawning_manager, monkeypatch
    ):
        monkeypatch.setattr(random, "random", lambda: 0.99)
        spawn_pos = complex_spawning_manager.get_natural_rice_spawn_location(set())
        assert spawn_pos is None

    def test_rice_does_not_spawn_on_occupied_tiles(
        self, complex_spawning_manager, monkeypatch
    ):
        monkeypatch.setattr(random, "random", lambda: 0.0)

        occupied_tiles = {
            (1, 1),
            (1, 2),
            (1, 3),
            (2, 1),
            (2, 3),
            (3, 1),
            (3, 2),
            (3, 3),
        }
        spawn_pos = complex_spawning_manager.get_natural_rice_spawn_location(
            occupied_tiles
        )
        assert spawn_pos is None


class TestSpawningIntegration:
    def test_eaten_rice_is_replanted_via_managers(
        self, simple_spawning_manager, mock_config
    ):
        """Tests the full replanting loop using (y, x) standard."""
        # ARRANGE
        tile_size = mock_config["simulation"]["tile_size_meters"]
        entity_manager = EntityManager(mock_config, tile_size)

        rice = entity_manager.create_rice(pos_y=1, pos_x=1)
        rice_pos_yx = (1, 1)  # Correct (y, x) format
        rice.get_eaten()

        # ACT 1: Cleanup and Queueing
        removed_entities = entity_manager.cleanup_dead_entities()
        assert len(removed_entities) == 1

        # This part simulates the logic from World.game_tick
        entity = removed_entities[0]
        if hasattr(entity, "is_eaten") and entity.is_eaten:
            # Correctly derive grid pos from world pos [y, x]
            grid_y = int(entity.position[0] / tile_size)
            grid_x = int(entity.position[1] / tile_size)
            simple_spawning_manager.add_to_replant_queue((grid_y, grid_x))

        # ASSERT 1: State is correct before the next tick
        assert len(entity_manager.entities) == 0
        assert len(simple_spawning_manager.replant_queue) == 1
        assert simple_spawning_manager.replant_queue[0] == rice_pos_yx

        # ACT 2: Process the queue and respawn
        coords_to_replant = simple_spawning_manager.process_replant_queue()
        for pos_y, pos_x in coords_to_replant:
            entity_manager.create_rice(pos_y, pos_x)

        # ASSERT 2: A new rice plant exists
        assert len(simple_spawning_manager.replant_queue) == 0
        assert len(entity_manager.entities) == 1
        new_rice = next(e for e in entity_manager.entities if isinstance(e, Rice))
        assert new_rice is not None
        assert new_rice.age == 0
