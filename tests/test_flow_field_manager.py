# tests/test_flow_field_manager.py

import pytest
import numpy as np
from domain.flow_field_manager import FlowFieldManager
from domain.tile import TILES


@pytest.fixture
def test_grid():
    """
    Provides a 5x5 grid with a 'U' shaped obstacle.
    L L L L L
    L W W W L
    L L G W L  (G = Goal will be at (2,2))
    L W W W L
    L L L L L
    """
    grid = [
        [TILES["land"]] * 5,
        [TILES["land"], TILES["water"], TILES["water"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["land"], TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["water"], TILES["water"], TILES["land"]],
        [TILES["land"]] * 5,
    ]
    return grid


@pytest.fixture
def flow_manager(test_grid):
    return FlowFieldManager(test_grid)


class TestFlowFieldManager:
    def test_field_generation_single_goal(self, flow_manager):
        # ARRANGE
        goal_pos = [(2, 2)]  # The 'G' in the diagram

        # ACT
        flow_field = flow_manager.generate_flow_field(goal_pos)

        # ASSERT (CORRECTED)
        # Check vectors to ensure they point towards the goal, navigating the obstacle.
        # Vector format is (dy, dx).

        # The shortest path from (0,0) is South, not South-East into water.
        assert np.array_equal(
            flow_field[0, 0], [1, 0]
        ), "From (0,0) should be S (dy=1, dx=0)"

        # From (0,2), the path goes East towards the gap at (1,2)
        assert np.array_equal(
            flow_field[2, 0], [0, 1]
        ), "From (0,2) should be E (dy=0, dx=1)"

        # From (4,4), the path is West towards (4,3) etc.
        assert np.array_equal(
            flow_field[4, 4], [0, -1]
        ), "From (4,4) should be W (dy=0, dx=-1)"

        # Position of the goal itself should be (0,0) as it has nowhere to go
        assert np.array_equal(
            flow_field[2, 2], [0, 0]
        ), "Goal tile vector should be zero"

        # Impassable water tiles should have a (0,0) vector
        assert np.array_equal(
            flow_field[1, 1], [0, 0]
        ), "Impassable tile vector should be zero"
        assert np.array_equal(
            flow_field[1, 2], [0, 0]
        ), "Impassable tile vector should be zero"

    def test_no_goals_results_in_zero_field(self, flow_manager):
        # ARRANGE
        goal_pos = []

        # ACT
        flow_field = flow_manager.generate_flow_field(goal_pos)

        # ASSERT
        # An empty goal list should result in a field of all (0,0) vectors.
        assert np.all(flow_field == 0)

    def test_unreachable_area_has_zero_vector(self):
        # ARRANGE
        # A grid where the goal is walled off.
        grid = [
            [TILES["land"], TILES["water"], TILES["land"]],
            [TILES["land"], TILES["water"], TILES["land"]],
            [TILES["land"], TILES["water"], TILES["land"]],
        ]
        manager = FlowFieldManager(grid)
        goal_pos = [(1, 2)]

        # ACT
        flow_field = manager.generate_flow_field(goal_pos)

        # ASSERT
        # The entire left side should be zero vectors because it can't reach the goal.
        assert np.array_equal(flow_field[0, 0], [0, 0])
        assert np.array_equal(flow_field[1, 0], [0, 0])
        assert np.array_equal(flow_field[2, 0], [0, 0])

        # The reachable side should have non-zero vectors (except the goal itself).
        assert np.array_equal(flow_field[0, 2], [1, 0])  # South (dy=1, dx=0)
        assert np.array_equal(flow_field[1, 2], [0, 0])  # The goal
        assert np.array_equal(flow_field[2, 2], [-1, 0])  # North (dy=-1, dx=0)

    def test_field_generation_multiple_goals(self, flow_manager):
        """
        Tests that the flow field correctly points to the NEAREST of two goals.
        """
        # ARRANGE
        # Goal A is at (0, 4) (top right)
        # Goal B is at (4, 0) (bottom left)
        goal_positions = [(0, 4), (4, 0)]

        # ACT
        flow_field = flow_manager.generate_flow_field(goal_positions)

        # ASSERT
        # The vector at (y, x) is (dy, dx)

        # Tiles near Goal A should point towards it.
        # (0, 3) is directly to the left of Goal A. Vector should be East (0, 1).
        assert np.array_equal(flow_field[0, 3], [0, 1]), "Should point East to Goal A"
        # (1, 4) is directly below Goal A. Vector should be North (-1, 0).
        assert np.array_equal(flow_field[1, 4], [-1, 0]), "Should point North to Goal A"

        # Tiles near Goal B should point towards it.
        # (4, 1) is directly to the right of Goal B. Vector should be West (0, -1).
        assert np.array_equal(flow_field[4, 1], [0, -1]), "Should point West to Goal B"
        # (3, 0) is directly above Goal B. Vector should be South (1, 0).
        assert np.array_equal(flow_field[3, 0], [1, 0]), "Should point South to Goal B"

        # Tiles from the obstacle near Goal A should point towards it.
        assert np.array_equal(flow_field[2, 2], [0, -1]), "Should point East to Goal A"

        # A tile equidistant from the obstacle-free path to both goals should pick one.
        # e.g. (0,0) is closer to Goal B (4,0)
        assert np.array_equal(
            flow_field[0, 0], [1, 0]
        ), "From (0,0) closer path is to Goal B"

        # The goals themselves have zero vectors
        assert np.array_equal(flow_field[0, 4], [0, 0]), "Goal A vector should be zero"
        assert np.array_equal(flow_field[4, 0], [0, 0]), "Goal B vector should be zero"
