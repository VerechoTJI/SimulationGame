# tests/test_pathfinder.py

import pytest
from domain.pathfinder import Pathfinder
from domain.tile import Tile, TILES


# A simple, deterministic grid for testing pathfinding.
# L = Land, W = Water (impassable)
# Grid layout:
# L L L  (y=0)
# L W L  (y=1)
# L L L  (y=2)
# x=0 x=1 x=2
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
    """Tests a straight path with no obstacles using (y, x) coords."""
    # From (y=0, x=0) to (y=0, x=2)
    path = pathfinder.find_path(start_pos_yx=(0, 0), end_pos_yx=(0, 2))
    assert path is not None
    assert path == [(0, 1), (0, 2)]


def test_pathfinder_around_obstacle(pathfinder):
    """Tests if the path correctly navigates around the water tile at (1, 1)."""
    # Path from top-left (0,0) to bottom-right (2,2) must go around water at (1,1)
    path = pathfinder.find_path(start_pos_yx=(0, 0), end_pos_yx=(2, 2))
    assert path is not None
    # Check that the path is valid and avoids the obstacle
    assert (
        len(path) > 2
    )  # It must be longer than a direct diagonal path if it were clear
    assert (1, 1) not in path, "Path must not go through water at (1, 1)"


def test_pathfinder_no_path_exists(pathfinder):
    """Tests a scenario where the destination is unreachable."""
    # Create a grid where the target is surrounded by water
    grid = [
        [TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["land"]],
    ]
    pathfinder_isolated = Pathfinder(grid)
    # Start at (y=0, x=0), end at (y=1, x=2) which is isolated
    path = pathfinder_isolated.find_path(start_pos_yx=(0, 0), end_pos_yx=(1, 2))
    assert path is None


def test_pathfinder_start_equals_end(pathfinder):
    """Tests if starting and ending at the same spot returns an empty path."""
    path = pathfinder.find_path(start_pos_yx=(0, 0), end_pos_yx=(0, 0))
    assert path == []


def test_pathfinder_start_on_impassable_tile(pathfinder):
    """Tests starting on an unwalkable tile (y=1, x=1) should find no path."""
    path = pathfinder.find_path(start_pos_yx=(1, 1), end_pos_yx=(2, 2))
    assert path is None
