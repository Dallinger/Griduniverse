"""Define the Griduniverse."""

import json
import random
import time
import uuid

from faker import Factory

from maze import generate_maze


class Gridworld(object):
    """A Gridworld in the Griduniverse."""
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
        self.food_visible = kwargs.get('food_visible')
        self.respawn_food = kwargs.get('respawn_food', True)
        self.dollars_per_point = kwargs.get('dollars_per_point', 0.02)
        self.num_colors = kwargs.get('num_colors', 2)
        self.mutable_colors = kwargs.get('mutable_colors', False)
        self.player_overlap = kwargs.get('player_overlap', True)
        self.background_animation = kwargs.get('background_animation', True)
        self.time = kwargs.get('time', 300)
        self.tax = kwargs.get('tax', 0.01)
        self.wall_type = kwargs.get('walls', None)
        self.walls_visible = kwargs.get('walls_visible', True)
        self.show_grid = kwargs.get('show_grid', None)
        self.visibility = kwargs.get('visibility', 5)
        self.motion_auto = kwargs.get('motion_auto', False)
        self.speed_limit = kwargs.get('speed_limit', 8)
        self.start_timestamp = kwargs.get('start_timestamp', time.time())
        self.motion_cost = kwargs.get('motion_cost', 0)
        self.initial_score = kwargs.get('initial_score', 0)
        self.motion_tremble_rate = kwargs.get('motion_tremble_rate', 0)
        self.frequency_dependence = kwargs.get('frequency_dependence', 0)
        self.frequency_dependent_payoff_rate = kwargs.get(
            'frequency_dependent_payoff_rate', 1)
        self.chatroom = kwargs.get('chatroom', False)
        self.contagion = kwargs.get('contagion', False)
        self.contagion_hierarchy = kwargs.get('contagion_hierarchy', False)
        self.donation = kwargs.get('donation', 0)
        self.pseudonyms = kwargs.get('pseudonyms', False)
        self.pseudonyms_locale = kwargs.get('pseudonyms_locale', 'en_US')
        self.food_reward = kwargs.get('food_reward', 1)

        self.walls = self.generate_walls(style=self.wall_type)

        for i in range(self.num_food):
            self.spawn_food()

        if self.contagion_hierarchy:
            self.contagion_hierarchy = range(self.num_colors)
            random.shuffle(self.contagion_hierarchy)

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
                    if self.respawn_food:
                        self.spawn_food()
                    player.score = player.score + self.food_reward
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
            speed_limit=self.speed_limit,
            motion_cost=self.motion_cost,
            score=self.initial_score,
            motion_tremble_rate=self.motion_tremble_rate,
            pseudonym_locale=self.pseudonyms_locale,
            grid=self,
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

    def spread_contagion(self):
        """Spread contagion."""
        color_updates = []
        for player in self.players:
            colors = [n.color for n in player.neighbors(d=self.contagion)]
            if colors:
                colors.append(player.color)
                plurality_color = max(colors, key=colors.count)
                if colors.count(plurality_color) > len(colors) / 2.0:
                    if (self.rank(plurality_color) < self.rank(player.color)):
                        color_updates.append((player, plurality_color))

        for (player, color) in color_updates:
            player.color = color

    def rank(self, color):
        """Where does this color fall on the color hierarchy?"""
        if self.contagion_hierarchy:
            return self.contagion_hierarchy[Gridworld.colors.index(color)]
        else:
            return 1


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

    def __init__(self, **kwargs):
        super(Player, self).__init__()

        self.id = kwargs.get('id', uuid.uuid4())
        self.position = kwargs.get('position', [0, 0])
        self.motion_auto = kwargs.get('motion_auto', False)
        self.motion_direction = kwargs.get('motion_direction', 'right')
        self.speed_limit = kwargs.get('speed_limit', 8)
        self.num_possible_colors = kwargs.get('num_possible_colors', 2)
        self.motion_cost = kwargs.get('motion_cost', 0)
        self.motion_tremble_rate = kwargs.get('motion_tremble_rate', 0)
        self.grid = kwargs.get('grid', None)
        self.score = kwargs.get('score', 0)
        self.pseudonym_locale = kwargs.get('pseudonym_locale', 'en_US')

        # Determine the player's color.
        if 'color' in kwargs:
            self.color_idx = Gridworld.colors.index(kwargs['color'])
        elif 'color_name' in kwargs:
            self.color_idx = Gridworld.color_names.index(kwargs['color_name'])
        else:
            self.color_idx = random.randint(0, self.num_possible_colors - 1)

        self.color_name = Gridworld.color_names[self.color_idx]
        self.color = Gridworld.colors[self.color_idx]

        # Determine the player's pseudonym.
        self.fake = Factory.create(self.pseudonym_locale)
        self.name = self.fake.name()

        self.motion_timestamp = 0

    def tremble(self, direction):
        """Change direction with some probability."""
        directions = [
            "up",
            "down",
            "left",
            "right"
        ]
        directions.remove(direction)
        direction = random.choice(directions)
        return direction

    def move(self, direction, tremble_rate=0):
        """Move the player."""

        if random.random() < tremble_rate:
            direction = self.tremble(direction)

        self.motion_direction = direction

        new_position = self.position[:]

        if direction == "up":
            if self.position[0] > 0:
                new_position[0] -= 1

        elif direction == "down":
            if self.position[0] < (self.grid.rows - 1):
                new_position[0] = self.position[0] + 1

        elif direction == "left":
            if self.position[1] > 0:
                new_position[1] = self.position[1] - 1

        elif direction == "right":
            if self.position[1] < (self.grid.columns - 1):
                new_position[1] = self.position[1] + 1

        # Update motion.
        now_relative = time.time() - self.grid.start_timestamp
        wait_time = 1.0 / self.speed_limit
        can_move = now_relative > (self.motion_timestamp + wait_time)

        can_afford_to_move = self.score >= self.motion_cost

        if can_move and can_afford_to_move:
            if (self.grid.player_overlap or (
                (not self.grid._has_player(new_position)) and
                (not self.grid._has_wall(new_position))
            )):
                self.position = new_position
                self.motion_timestamp = now_relative
                self.score -= self.motion_cost

    def is_neighbor(self, player, d=1):
        """Determine whether other player is adjacent."""
        manhattan_distance = (
            abs(self.position[0] - player.position[0]) +
            abs(self.position[1] - player.position[1])
        )
        return (manhattan_distance <= d)

    def neighbors(self, d=1):
        """Return all adjacent players."""
        return [
            p for p in self.grid.players if (
                self.is_neighbor(p, d=d) and (p is not self)
            )
        ]

    def serialize(self):
        return {
            "id": self.id,
            "position": self.position,
            "score": self.score,
            "color": self.color,
            "motion_auto": self.motion_auto,
            "motion_direction": self.motion_direction,
            "speed_limit": self.speed_limit,
            "motion_timestamp": self.motion_timestamp,
            "name": self.name,
        }
