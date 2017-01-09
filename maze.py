import random


def generate_maze(columns=20, rows=20):

    c = (columns - 1) / 2
    r = (rows - 1) / 2

    visited = [[0] * c + [1] for _ in range(r)] + [[1] * (c + 1)]
    ver = [["* "] * c + ['*'] for _ in range(r)] + [[]]
    hor = [["**"] * c + ['*'] for _ in range(r + 1)]

    sx = random.randrange(c)
    sy = random.randrange(r)
    visited[sy][sx] = 1
    stack = [(sx, sy)]
    while len(stack) > 0:
        (x, y) = stack.pop()
        d = [
            (x - 1, y),
            (x, y + 1),
            (x + 1, y),
            (x, y - 1)
        ]
        random.shuffle(d)
        for (xx, yy) in d:
            if visited[yy][xx]:
                continue
            if xx == x:
                hor[max(y, yy)][x] = "* "
            if yy == y:
                ver[y][max(x, xx)] = "  "
            stack.append((xx, yy))
            visited[yy][xx] = 1

    # Convert the maze to a list of wall cell positions.
    the_rows = ([j for i in zip(hor, ver) for j in i])
    the_rows = [list("".join(j)) for j in the_rows]
    maze = [item is '*' for sublist in the_rows for item in sublist]
    walls = []
    for idx in range(len(maze)):
        if maze[idx]:
            walls.append((idx / columns, idx % columns))

    # s = ""
    # for (a, b) in zip(hor, ver):
    #     s += ''.join(a + ['\n'] + b + ['\n'])
    # print(s)

    return walls


if __name__ == '__main__':
    print(generate_maze(columns=25, rows=25))
