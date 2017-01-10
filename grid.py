"""Define the Griduniverse."""

import json
import random
import uuid

from maze import generate_maze


class Gridworld(object):
    """A Gridworld in the Griduniverse."""
    def __init__(self, **kwargs):
        super(Gridworld, self).__init__()

        self.players = []
        self.food = []
        self.food_consumed = []

        self.num_players = kwargs.get('num_players', 4)
        self.columns = kwargs.get('columns', 25)
        self.rows = kwargs.get('rows', 25)
        self.block_size = kwargs.get('block_size', 15)
        self.padding = kwargs.get('padding', 1)
        self.num_food = kwargs.get('num_food', self.num_players - 1)
        self.respawn_food = kwargs.get('respawn_food', True)
        self.dollars_per_point = kwargs.get('dollars_per_point', 0.02)
        self.num_colors = kwargs.get('num_colors', 2)
        self.mutable_colors = kwargs.get('mutable_colors', False)
        self.player_overlap = kwargs.get('player_overlap', True)
        self.background_animation = kwargs.get('background_animation', True)
        self.time = kwargs.get('time', 300)
        self.tax = kwargs.get('tax', 0.01)
        self.wall_type = kwargs.get('walls', None)
        self.show_grid = kwargs.get('show_grid', None)
        self.visibility = kwargs.get('visibility', 5)

        self.walls = self.generate_walls(style=self.wall_type)

        for i in range(self.num_food):
            self.spawn_food()

    def serialize(self):
        return json.dumps({
            "players": [player.serialize() for player in self.players],
            "food": [food.serialize() for food in self.food],
            "walls": [wall.serialize() for wall in self.walls],
        })

    def consume(self):
        """Players consume the food."""
        for food in self.food:
            for player in self.players:
                if food.position == player.position:
                    self.food_consumed.append(food)
                    self.food.remove(food)
                    self.spawn_food()
                    player.score = player.score + 1
                    break

    def spawn_food(self):
        """Respawn the food."""
        self.food.append(Food(
            id=(len(self.food) + len(self.food_consumed)),
            position=self._random_empty_position(),
            color=[1.00, 1.00, 1.00],
        ))

    def spawn_player(self, id=None):
        """Spawn a player."""
        player = Player(
            id=id,
            position=self._random_empty_position(),
            num_possible_colors=self.num_colors,
        )
        self.players.append(player)

    def generate_walls(self, style=None):
        """Generate the walls."""
        if style is None:
            walls = []
        elif style is "maze":
            maze = generate_maze(columns=self.columns, rows=self.rows)
            walls = []
            for w in maze:
                walls.append(Wall(position=[w[0], w[1]]))

        return walls

    def _random_empty_position(self):
        """Select an empty cell at random."""
        empty_cell = False
        while (not empty_cell):
            position = [
                random.randint(0, self.rows - 1),
                random.randint(0, self.columns - 1),
            ]
            empty_cell = self._empty(position)

        return position

    def _empty(self, position):
        """Determine whether a particular cell is empty."""
        return not (
            self._has_player(position) or
            self._has_food(position) or
            self._has_wall(position)
        )

    def _has_player(self, position):
        for player in self.players:
            if player.position == position:
                return True
        return False

    def _has_food(self, position):
        for food in self.food:
            if food.position == position:
                return True
        return False

    def _has_wall(self, position):
        for wall in self.walls:
            if wall.position == position:
                return True
        return False


class Food(object):
    """Food."""
    def __init__(self, **kwargs):
        super(Food, self).__init__()

        self.id = kwargs.get('id', uuid.uuid4())
        self.position = kwargs.get('position', [0, 0])
        self.color = kwargs.get('color', [0.5, 0.5, 0.5])

    def serialize(self):
        return {
            "id": self.id,
            "position": self.position,
        }


class Wall(object):
    """Wall."""
    def __init__(self, **kwargs):
        super(Wall, self).__init__()

        self.position = kwargs.get('position', [0, 0])
        self.color = kwargs.get('color', [0.5, 0.5, 0.5])

    def serialize(self):
        return {
            "position": self.position,
            "color": self.color,
        }


class Player(object):
    """A player."""
    color_names = [
        "blue",
        "yellow",
        "green",
        "red",
    ]
    colors = [
        [0.50, 0.86, 1.00],
        [1.00, 0.86, 0.50],
        [0.56, 0.60, 0.16],
        [0.64, 0.11, 0.31],
    ]

    def __init__(self, **kwargs):
        super(Player, self).__init__()

        self.id = kwargs.get('id', uuid.uuid4())
        self.position = kwargs.get('position', [0, 0])
        self.motion_auto = kwargs.get('motion_auto', False)
        self.motion_direction = kwargs.get('motion_direction', 'right')
        self.motion_speed = kwargs.get('motion_speed', 8)
        self.num_possible_colors = kwargs.get('num_possible_colors', 2)

        # Determine the player's color.
        if 'color' in kwargs:
            self.color_idx = Player.colors.index(kwargs['color'])
        elif 'color_name' in kwargs:
            self.color_idx = Player.color_names.index(kwargs['color_name'])
        else:
            self.color_idx = random.randint(0, self.num_possible_colors - 1)

        self.color_name = Player.color_names[self.color_idx]
        self.color = Player.colors[self.color_idx]

        self.motion_timestamp = 0
        self.score = 0

    def move(self, direction, grid):
        """Move the player."""

        self.motion_direction = direction

        new_position = self.position[:]

        if direction == "up":
            if self.position[0] > 0:
                new_position[0] -= 1

        elif direction == "down":
            if self.position[0] < (grid.rows - 1):
                new_position[0] = self.position[0] + 1

        elif direction == "left":
            if self.position[1] > 0:
                new_position[1] = self.position[1] - 1

        elif direction == "right":
            if self.position[1] < (grid.columns - 1):
                new_position[1] = self.position[1] + 1

        if (grid.player_overlap or (
            (not grid._has_player(new_position)) and
            (not grid._has_wall(new_position))
        )):
            self.position = new_position

    def serialize(self):
        return {
            "id": self.id,
            "position": self.position,
            "score": self.score,
            "color": self.color,
            "motion_auto": self.motion_auto,
            "motion_direction": self.motion_direction,
            "motion_speed": self.motion_speed,
            "motion_timestamp": self.motion_timestamp,
        }
