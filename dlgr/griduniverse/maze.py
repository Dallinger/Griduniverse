import gevent
import itertools
import random


class Wall(object):
    """A segment of colored wall occupying a single grid postion"""

    DEFAULT_COLOR = [0.5, 0.5, 0.5]

    def __init__(self, **kwargs):
        self.position = kwargs.get("position", [0, 0])
        self.color = kwargs.get("color", self.DEFAULT_COLOR)

    def serialize(self):
        if self.color != self.DEFAULT_COLOR:
            return {
                "position": self.position,
                "color": self.color,
            }
        else:
            return self.position


def labyrinth(columns=25, rows=25, density=1.0, contiguity=1.0):
    """Builds a labyrinth of Wall objects of a given size, with a given
    density and contiguity. A density of 1.0 will produce a maze that
    is 50% Wall and 50% open space. A contiguity of 1.0 will produce a maze with
    no neighborless Walls. A contiguity < 1 will be increasingly likely to
    contain neighborless Walls.
    """
    if density:
        walls = [Wall(position=pos) for pos in _generate(rows, columns)]
        # Add sleep to avoid timeouts
        gevent.sleep(0.00001)
        return _prune(walls, density, contiguity)
    else:
        return []


def _generate(rows, columns):
    """Generate an initial maze with 50% wall and 50% space."""
    c = (columns - 1) // 2
    r = (rows - 1) // 2
    visited = [[0] * c + [1] for _ in range(r)] + [[1] * (c + 1)]
    ver = [["* "] * c + ["*"] for _ in range(r)] + [[]]
    hor = [["**"] * c + ["*"] for _ in range(r + 1)]

    # Select a starting position at random, and mark it as visited:
    sx = random.randrange(c)
    sy = random.randrange(r)
    visited[sy][sx] = 1

    stack = [(sx, sy)]
    while len(stack) > 0:
        (x, y) = stack.pop()
        d = [(x - 1, y), (x, y + 1), (x + 1, y), (x, y - 1)]
        random.shuffle(d)
        for xx, yy in d:
            if visited[yy][xx]:
                continue
            if xx == x:
                hor[max(y, yy)][x] = "* "
            if yy == y:
                ver[y][max(x, xx)] = "  "
            stack.append((xx, yy))
            visited[yy][xx] = 1

    # Convert the maze to a list of wall cell positions.
    the_rows = [j for i in zip(hor, ver) for j in i]
    the_rows = [list("".join(j)) for j in the_rows]
    maze = [item == "*" for sublist in the_rows for item in sublist]
    positions = []
    for idx, value in enumerate(maze):
        if value:
            positions.append([idx // columns, idx % columns])

    return positions


def _prune(walls, density, contiguity):
    """Prune walls to a labyrinth with the given density and contiguity."""
    num_to_prune = int(round(len(walls) * (1 - density)))
    num_pruned = 0
    while num_pruned < num_to_prune:
        to_prune = _classify_terminals(walls, limit=num_to_prune - num_pruned)
        walls = [w for i, w in enumerate(walls) if i not in to_prune]
        if len(to_prune) == 0:
            break
        num_pruned += len(to_prune)

    num_to_prune = int(round(len(walls) * (1 - contiguity)))
    to_prune = set(random.sample(range(len(walls)), num_to_prune))
    walls = [w for i, w in enumerate(walls) if i not in to_prune]

    return walls


def _classify_terminals(walls, limit=None):
    found = [set()]
    unmatched = {}
    enumerated_walls = tuple(enumerate(walls))
    position_map = {tuple(w.position): i for i, w in enumerated_walls}

    for i, w in enumerated_walls:
        neighbors = set()
        for adj in ([1, 0], [-1, 0], [0, 1], [0, -1]):
            neighbor = tuple(p1 + p2 for p1, p2 in zip(w.position, adj))
            if neighbor in position_map:
                neighbors.add(neighbor)
        if len(neighbors) <= 1:
            found[0].add(i)
            if limit and len(found[0]) >= limit:
                break
        elif len(neighbors) == 2:
            n_indexes = {position_map[i] for i in neighbors}
            j = 0
            while j < len(found):
                if n_indexes.intersection(found[j]):
                    if len(found) < j + 2:
                        found.append(set())
                    up_next = found[j + 1]
                    up_next.add(i)
                    break
                j += 1
            else:
                unmatched[i] = n_indexes

    for index in unmatched:
        j = 0
        n_indexes = unmatched[index]
        while j < len(found):
            if n_indexes.intersection(found[j]):
                if len(found) < j + 2:
                    found.append(set())
                up_next = found[j + 1]
                up_next.add(index)
                break
            j += 1

    to_prune = set()
    for entries in found:
        if len(to_prune) < limit:
            to_prune = to_prune.union(
                set(itertools.islice(entries, limit - len(to_prune)))
            )
    return to_prune
