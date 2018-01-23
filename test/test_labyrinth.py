from collections import namedtuple
import pytest


class TestLabyrinth(object):

    @pytest.fixture
    def labyrinth(self, **kw):
        from dlgr.griduniverse.maze import labyrinth
        return labyrinth

    def test_creates_walls(self, labyrinth):
        from dlgr.griduniverse.maze import Wall
        walls = labyrinth()
        assert isinstance(walls[0], Wall)

    def test_defaults_to_25x25(self, labyrinth):
        walls = labyrinth()
        maxX = max([wall.position[0] for wall in walls])
        maxY = max([wall.position[1] for wall in walls])
        assert maxX == maxY == 24  # zero-index

    def test_zero_density_includes_no_walls(self, labyrinth):
        walls = labyrinth(columns=4, rows=4, density=0.0)
        assert len(walls) == 0

    def test_full_density_results_in_50_percent_wall(self, labyrinth):
        walls = labyrinth(columns=10, rows=10)
        assert len(walls) == 50

    def test_reducing_density_reduces_wall_count_correspondingly(self, labyrinth):
        walls = labyrinth(columns=10, rows=10, density=0.5)
        assert len(walls) == 25

    def test_reducing_density_and_contiguity_reduces_wall_count_by_sum(self, labyrinth):
        walls = labyrinth(columns=10, rows=10, density=0.5, contiguity=0.5)
        assert len(walls) == 12  # 50 * .5. * .5, rounded down.


class TestMazePrune(object):

    @pytest.fixture
    def prune(self, **kw):
        from dlgr.griduniverse import maze
        return maze._prune

    @pytest.fixture
    def Pos(self):
        Positioned = namedtuple('Positioned', ['position'])
        return Positioned

    def test_prune_removes_isolated_walls_only_when_contiguity_is_1(self, Pos, prune):
        """Before:
        [
                                                                [0, 7], [0, 8],
                                                                [1, 7], [1, 8],
        [2, 0],                 [2, 3],                 [2, 6], [2, 7],
                [3, 1],                         [3, 5], [3, 6],                 [3, 9],
        [4, 0],         [4, 2],         [4, 4], [4, 5],
                                [5, 3], [5, 4],                 [5, 7],
                [6, 1], [6, 2], [6, 3],
                [7, 1], [7, 2], [7, 3],
        [8, 0]
        ]

        After:
        [
                                                                 [0, 7], [0, 8],
                                                                 [1, 7], [1, 8],
                                                         [2, 6], [2, 7],
                                                 [3, 5], [3, 6],
                                         [4, 4], [4, 5],
                                 [5, 3], [5, 4],
                 [6, 1], [6, 2], [6, 3],
                 [7, 1], [7, 2], [7, 3]
        ]

        """
        positions = [
            [0, 7], [0, 8],
            [1, 7], [1, 8],
            [2, 0], [2, 3], [2, 6], [2, 7],
            [3, 1], [3, 5], [3, 6], [3, 9],
            [4, 0], [4, 2], [4, 4], [4, 5],
            [5, 3], [5, 4], [5, 7],
            [6, 1], [6, 2], [6, 3],
            [7, 1], [7, 2], [7, 3],
            [8, 0]
        ]
        walls = [Pos(pos) for pos in positions]
        pruned = [
            w.position for w in prune(walls, density=0.5, contiguity=1.0)
        ]
        singles_removed = [
            [0, 7], [0, 8],
            [1, 7], [1, 8],
            [2, 6], [2, 7],
            [3, 5], [3, 6],
            [4, 4], [4, 5],
            [5, 3], [5, 4],
            [6, 1], [6, 2], [6, 3],
            [7, 1], [7, 2], [7, 3]
        ]
        assert pruned == singles_removed

    def test_prune_removes_some_contiguous_walls_with_contiguity_less_than_1(self, Pos, prune):
        positions = [
            [0, 7], [0, 8],
            [1, 7], [1, 8],
            [2, 0], [2, 3], [2, 6], [2, 7],
            [3, 1], [3, 5], [3, 6], [3, 9],
            [4, 0], [4, 2], [4, 4], [4, 5],
            [5, 3], [5, 4], [5, 7],
            [6, 1], [6, 2], [6, 3],
            [7, 1], [7, 2], [7, 3],
            [8, 0]
        ]
        num_with_neighbors = 18  # 18 of 26 walls have neighbors in this configuration
        walls = [Pos(pos) for pos in positions]
        pruned = [
            w.position for w in prune(walls, density=0.5, contiguity=0.5)
        ]

        assert len(pruned) < num_with_neighbors
