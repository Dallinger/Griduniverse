# The MIT License (MIT)
#
# Copyright (c) 2015 Bryukhanov Valentin
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
from heapq import heappop, heappush


def maze_to_graph(maze):
    height = len(maze)
    width = len(maze[0]) if height else 0
    graph = {(i, j): [] for j in range(width) for i in range(height) if not maze[i][j]}
    for row, col in graph.keys():
        if row < height - 1 and not maze[row + 1][col]:
            graph[(row, col)].append(("S", (row + 1, col)))
            graph[(row + 1, col)].append(("N", (row, col)))
        if col < width - 1 and not maze[row][col + 1]:
            graph[(row, col)].append(("E", (row, col + 1)))
            graph[(row, col + 1)].append(("W", (row, col)))
    return graph


def heuristic(cell, goal):
    return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])


def find_path_astar(maze, start, goal, max_iterations=None, graph=None):
    pr_queue = []
    heappush(pr_queue, (0 + heuristic(start, goal), 0, "", start))
    visited = set()
    if maze[start[0]][start[1]] == 1:
        return None
    if maze[goal[0]][goal[1]] == 1:
        return None
    if graph is None:
        graph = maze_to_graph(maze)
    i = 0
    while pr_queue:
        i += 1
        if max_iterations and i > max_iterations:
            expected, cost, path, current = sorted(pr_queue, key=lambda x: x[0])[0]
            return expected, path, current
        _, cost, path, current = heappop(pr_queue)
        if current == goal:
            return cost, path, current
        if current in visited:
            continue
        visited.add(current)
        for direction, neighbour in graph[current]:
            heappush(pr_queue, (cost + heuristic(neighbour, goal), cost + 1,
                                path + direction, neighbour))
    return None, ""


def labyrinth_to_maze(labyrinth, rows, columns):
    wall_positions = {tuple(w.position) for w in labyrinth}
    return positions_to_maze(wall_positions, rows, columns)


def positions_to_maze(wall_positions, rows, columns):
    maze_rows = []
    for i in range(rows):
        row = []
        for j in range(columns):
            row.append(int((i, j) in wall_positions))
        maze_rows.append(row)
    return maze_rows
