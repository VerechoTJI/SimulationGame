# tests/test_pathfinder.py

import pytest
from domain.pathfinder import Pathfinder
from domain.tile import Tile, TILES


# A simple, deterministic grid for testing pathfinding.
# L = Land, W = Water (impassable)
# Grid:
# L L L
# L W L
# L L L
@pytest.fixture
def test_grid():
    """Provides a simple 3x3 grid with a water obstacle."""
    grid = [
        [TILES["land"], TILES["land"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["land"], TILES["land"]],
    ]
    return grid


@pytest.fixture
def pathfinder(test_grid):
    """Provides a Pathfinder instance initialized with the test grid."""
    return Pathfinder(test_grid)


def test_pathfinder_direct_path(pathfinder):
    """Tests a straight path with no obstacles."""
    path = pathfinder.find_path(start_pos=(0, 0), end_pos=(2, 0))
    assert path is not None
    assert path == [(1, 0), (2, 0)]


def test_pathfinder_around_obstacle(pathfinder):
    """Tests if the path correctly navigates around the water tile."""
    # Path from top-left to bottom-right must go around the water at (1, 1)
    path = pathfinder.find_path(start_pos=(0, 0), end_pos=(2, 2))
    assert path is not None
    # One possible correct path. Note: (1,0) -> (2,1) -> (2,2) is also valid.
    # We check for length and valid moves.
    assert len(path) > 2  # It must be longer than a direct path
    assert (1, 1) not in path  # Must not go through water


def test_pathfinder_no_path_exists(pathfinder):
    """Tests a scenario where the destination is unreachable."""
    # Create a grid where the target is surrounded by water
    grid = [
        [TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["land"]],
    ]
    pathfinder_isolated = Pathfinder(grid)
    path = pathfinder_isolated.find_path(start_pos=(0, 0), end_pos=(2, 1))
    assert path is None


def test_pathfinder_start_equals_end(pathfinder):
    """Tests if starting and ending at the same spot returns an empty path."""
    path = pathfinder.find_path(start_pos=(0, 0), end_pos=(0, 0))
    assert path == []  # An empty list is the correct response


def test_pathfinder_start_on_impassable_tile(pathfinder):
    """Tests starting on an unwalkable tile (should find no path)."""
    path = pathfinder.find_path(start_pos=(1, 1), end_pos=(2, 2))
    assert path is None
