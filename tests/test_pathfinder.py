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


def test_pathfinder_with_tile_cost():
    """Tests if the path correctly choose a cheaper path."""
    # ARRANGE
    grid = [
        [TILES["land"], TILES["land"], TILES["land"]],
        [TILES["land"], TILES["mountain"], TILES["land"]],
        [TILES["land"], TILES["mountain"], TILES["land"]],
    ]
    # ACT
    pathfinder = Pathfinder(grid)
    path = pathfinder.find_path(start_pos_yx=(1, 0), end_pos_yx=(1, 2))

    # ASSERT
    # Check that the path should exist
    assert path is not None
    # Path (0, 1) -> (1, 2) should be the cheapest
    assert path[0] == (0, 1) and path[1] == (1, 2)


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


def test_find_path_avoids_diagonal_corner_cutting():
    """
    Tests that A* does not produce a path that "cuts the corner"
    of an impassable tile.
    Grid:
      S . .   S=Start (0,0)
      . W .   W=Water (1,1)
      . . E   E=End (2,2)
    The path from S to E should not be [(1,0), (2,1), (2,2)] by cutting
    across the corner of the water. It must go around. The shortest valid
    path would be something like [(1,0), (2,0), (2,1), (2,2)].
    """
    # ARRANGE
    grid = [
        [TILES["land"], TILES["land"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["land"], TILES["land"]],
    ]
    pathfinder = Pathfinder(grid)
    start_pos_yx = (0, 0)
    end_pos_yx = (2, 2)

    # ACT
    path = pathfinder.find_path(start_pos_yx, end_pos_yx)

    # ASSERT
    # The failing path would be (0,0) -> (1,1) diagonally.
    # A correct path must go around, e.g., (0,0) -> (0,1) -> (1,2) -> (2,2).
    # We can check this by asserting that the path does not contain
    # any two consecutive diagonal points that "straddle" an impassable node.
    # For this specific case, path should not contain (1,2) immediately after (0,1)
    # if it means crossing the (1,1) corner.
    # The easiest check is to assert the expected path.
    # One valid path is [(1, 0), (2, 0), (2, 1), (2, 2)]
    # Another is [(0, 1), (1, 2), (2, 2)] (depending on tie-breaking)
    # Let's ensure the direct diagonal isn't taken.
    assert path is not None
    assert path != [(1, 1)], "Path should not go directly through the impassable tile."

    # More robustly check the corner-cutting rule
    # The path from (0,0) to (2,2) must go around (1,1).
    # e.g. [(0,1), (1,2), (2,2)] is a valid path.
    # The invalid path would try to go from (0,0) to (1,1)
    # or from (0,2) to (1,1), etc.
    # In our implementation, path does not include start node.
    expected_path_1 = [(1, 0), (2, 1), (2, 2)]  # Incorrect path, but might be produced
    expected_path_2 = [(0, 1), (0, 2), (1, 2), (2, 2)]  # Correct
    expected_path_3 = [(1, 0), (2, 0), (2, 1), (2, 2)]  # Also Correct

    assert (
        path == expected_path_2 or path == expected_path_3
    ), f"Path {path} is not a valid path that avoids corner cutting."
