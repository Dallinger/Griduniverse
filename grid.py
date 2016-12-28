"""Define the Griduniverse."""

import json
import random
import uuid


class Gridworld(object):
    """A Gridworld in the Griduniverse."""
    def __init__(self, **kwargs):
        super(Gridworld, self).__init__()

        self.players = []
        self.food = []
        self.food_consumed = []

        self.num_players = kwargs.get('num_players', 4)
        self.columns = kwargs.get('columns', 20)
        self.rows = kwargs.get('rows', 20)
        self.grid_block_size = kwargs.get('grid_block_size', 15)
        self.grid_padding = kwargs.get('grid_padding', 1)
        self.respawn_food = kwargs.get('respawn_food', True)
        self.dollars_per_point = kwargs.get('dollars_per_point', 0.02)

    def serialize(self):
        return json.dumps({
            "players": [player.serialize() for player in self.players],
            "food": [food.serialize() for food in self.food],
        })

    def consume(self):
        """Players consume the food."""
        for food in self.food:
            for player in self.players:
                if food.position == player.position:
                    self.food_consumed.append(food)
                    self.food.remove(food)
                    self.respawn()
                    player.score = player.score + 1
                    break

    def respawn(self):
        """Respawn the food."""
        self.food.append(Food(
            id=(len(self.food) + len(self.food_consumed)),
            position=[
                random.randint(0, self.columns - 1),
                random.randint(0, self.rows - 1),
            ],
            color=[1.00, 1.00, 1.00],
        ))


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


class Player(object):
    """A player."""
    def __init__(self, **kwargs):
        super(Player, self).__init__()

        self.id = kwargs.get('id', uuid.uuid4())
        self.position = kwargs.get('position', [0, 0])
        self.color = kwargs.get('color', [0.5, 0.5, 0.5])
        self.motion_auto = kwargs.get('motion_auto', False)
        self.motion_direction = kwargs.get('motion_direction', 'right')
        self.motion_speed = kwargs.get('motion_speed', 8)
        self.motion_timestamp = 0

        self.score = 0

    def move(self, direction, rows=20, columns=20):
        """Move the player."""

        self.motion_direction = direction

        if direction == "up":
            if self.position[0] > 0:
                self.position[0] -= 1

        elif direction == "down":
            if self.position[0] < (rows - 1):
                self.position[0] = self.position[0] + 1

        elif direction == "left":
            if self.position[1] > 0:
                self.position[1] = self.position[1] - 1

        elif direction == "right":
            if self.position[1] < (columns - 1):
                self.position[1] = self.position[1] + 1

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
