"""The Griduniverse."""

import datetime
import flask
import gevent
import itertools
import json
import logging
import math
import os
import random
import string
import time
import uuid
import yaml

from cached_property import cached_property
from dataclasses import dataclass, field
from faker import Factory
from sqlalchemy import create_engine
from sqlalchemy import func
from sqlalchemy.orm import (
    sessionmaker,
    scoped_session,
)

import dallinger
from dallinger import db
from dallinger.compat import unicode
from dallinger.config import get_config
from dallinger.experiment import Experiment

from . import distributions
from .maze import Wall
from .maze import labyrinth
from .bots import Bot
from .models import Event

logger = logging.getLogger(__file__)


GAME_CONFIG_FILE = "game_config.yml"

# Make bot importable without triggering style warnings
Bot = Bot

GU_PARAMS = {
    "network": unicode,
    "max_participants": int,
    "bot_policy": unicode,
    "num_rounds": int,
    "time_per_round": float,
    "instruct": bool,
    "columns": int,
    "rows": int,
    "window_columns": int,
    "window_rows": int,
    "block_size": int,
    "padding": int,
    "chat_visibility_threshold": float,
    "spatial_chat": bool,
    "visibility": int,
    "visibility_ramp_time": int,
    "background_animation": bool,
    "player_overlap": bool,
    "leaderboard_group": bool,
    "leaderboard_individual": bool,
    "leaderboard_time": int,
    "motion_speed_limit": float,
    "motion_auto": bool,
    "motion_cost": float,
    "motion_tremble_rate": float,
    "show_chatroom": bool,
    "show_grid": bool,
    "others_visible": bool,
    "num_colors": int,
    "mutable_colors": bool,
    "costly_colors": bool,
    "pseudonyms": bool,
    "pseudonyms_locale": unicode,
    "pseudonyms_gender": unicode,
    "contagion": int,
    "contagion_hierarchy": bool,
    "walls_density": float,
    "walls_contiguity": float,
    "walls_visible": bool,
    "initial_score": int,
    "dollars_per_point": float,
    "tax": float,
    "relative_deprivation": float,
    "frequency_dependence": float,
    "frequency_dependent_payoff_rate": float,
    "donation_amount": int,
    "donation_individual": bool,
    "donation_group": bool,
    "donation_ingroup": bool,
    "donation_public": bool,
    "difi_question": bool,
    "difi_group_label": unicode,
    "difi_group_image": unicode,
    "fun_survey": bool,
    "pre_difi_question": bool,
    "pre_difi_group_label": unicode,
    "pre_difi_group_image": unicode,
    "leach_survey": bool,
    "intergroup_competition": float,
    "intragroup_competition": float,
    "identity_signaling": bool,
    "identity_starts_visible": bool,
    "score_visible": bool,
    "alternate_consumption_donation": bool,
    "use_identicons": bool,
    "build_walls": bool,
    "wall_building_cost": int,
    "donation_multiplier": float,
    "num_recruits": int,
    "state_interval": float,
}

DEFAULT_ITEM_CONFIG = {
    1: {
        "item_id": 1,
        "name": "Food",
        "calories": 1,
    }
}


class PluralFormatter(string.Formatter):
    def format_field(self, value, format_spec):
        if format_spec.startswith("plural"):
            words = format_spec.split(",")
            if value == 1 or value == "1" or value == 1.0:
                return words[1]
            else:
                return words[2]
        else:
            return super(PluralFormatter, self).format_field(value, format_spec)


formatter = PluralFormatter()


def softmax(vector, temperature=1):
    """The softmax activation function."""
    vector = [math.pow(x, temperature) for x in vector]
    if sum(vector):
        return [float(x) / sum(vector) for x in vector]
    else:
        return [float(len(vector)) for _ in vector]


class Gridworld(object):
    """A Gridworld in the Griduniverse."""

    player_color_names = ["BLUE", "YELLOW", "ORANGE", "RED", "PURPLE", "TEAL"]

    player_colors = [
        [0.50, 0.86, 1.00],
        [1.00, 0.86, 0.50],
        [0.91, 0.50, 0.02],
        [0.64, 0.11, 0.31],
        [0.85, 0.60, 0.85],
        [0.77, 0.96, 0.90],
    ]

    GREEN = [0.51, 0.69, 0.61]
    WHITE = [1.00, 1.00, 1.00]
    wall_locations = None
    item_locations = None
    walls_updated = True
    items_updated = True

    def __new__(cls, **kwargs):
        if not hasattr(cls, "instance"):
            cls.instance = super(Gridworld, cls).__new__(cls)
        return cls.instance

    def __init__(self, **kwargs):
        # If Singleton is already initialized, do nothing
        if hasattr(self, "num_players"):
            return

        self.log_event = kwargs.get("log_event", lambda x: None)

        # Players
        self.num_players = kwargs.get("max_participants", 3)

        # Rounds
        self.num_rounds = kwargs.get("num_rounds", 1)
        self.time_per_round = kwargs.get("time_per_round", 300)

        # Instructions
        self.instruct = kwargs.get("instruct", True)

        # Grid
        self.columns = kwargs.get("columns", 25)
        self.rows = kwargs.get("rows", 25)
        self.window_columns = kwargs.get("window_columns", min(self.columns, 25))
        self.window_rows = kwargs.get("window_rows", min(self.rows, 25))
        self.block_size = kwargs.get("block_size", 10)
        self.padding = kwargs.get("padding", 1)
        self.chat_visibility_threshold = kwargs.get("chat_visibility_threshold", 0.4)
        self.spatial_chat = kwargs.get("spatial_chat", False)
        self.visibility = kwargs.get("visibility", 40)
        self.visibility_ramp_time = kwargs.get("visibility_ramp_time", 4)
        self.background_animation = kwargs.get("background_animation", True)
        self.player_overlap = kwargs.get("player_overlap", False)

        # Motion
        self.motion_speed_limit = kwargs.get("motion_speed_limit", 8)
        self.motion_auto = kwargs.get("motion_auto", False)
        self.motion_cost = kwargs.get("motion_cost", 0)
        self.motion_tremble_rate = kwargs.get("motion_tremble_rate", 0)

        # Components
        self.show_chatroom = kwargs.get("show_chatroom", False)
        self.show_grid = kwargs.get("show_grid", True)

        # Identity
        self.others_visible = kwargs.get("others_visible", True)
        self.num_colors = kwargs.get("num_colors", 3)
        self.mutable_colors = kwargs.get("mutable_colors", False)
        self.costly_colors = kwargs.get("costly_colors", False)
        self.pseudonyms = kwargs.get("pseudonyms", True)
        self.pseudonyms_locale = kwargs.get("pseudonyms_locale", "en_US")
        self.pseudonyms_gender = kwargs.get("pseudonyms_gender", None)
        self.contagion = kwargs.get("contagion", 0)
        self.contagion_hierarchy = kwargs.get("contagion_hierarchy", False)
        self.identity_signaling = kwargs.get("identity_signaling", False)
        self.identity_starts_visible = kwargs.get("identity_starts_visible", False)
        self.use_identicons = kwargs.get("use_identicons", False)

        # Walls
        self.walls_visible = kwargs.get("walls_visible", True)
        self.walls_density = kwargs.get("walls_density", 0.0)
        self.walls_contiguity = kwargs.get("walls_contiguity", 1.0)
        self.build_walls = kwargs.get("build_walls", False)
        self.wall_building_cost = kwargs.get("wall_building_cost", 0)
        self.wall_locations = {}

        # Payoffs
        self.initial_score = kwargs.get("initial_score", 0)
        self.dollars_per_point = kwargs.get("dollars_per_point", 0.02)
        self.tax = kwargs.get("tax", 0.00)
        self.relative_deprivation = kwargs.get("relative_deprivation", 1)
        self.frequency_dependence = kwargs.get("frequency_dependence", 0)
        self.frequency_dependent_payoff_rate = kwargs.get(
            "frequency_dependent_payoff_rate", 0
        )
        self.leaderboard_group = kwargs.get("leaderboard_group", False)
        self.leaderboard_individual = kwargs.get("leaderboard_individual", False)
        self.leaderboard_time = kwargs.get("leaderboard_time", 0)

        # Donations
        self.donation_amount = kwargs.get("donation_amount", 0)
        self.donation_multiplier = kwargs.get("donation_multiplier", 1.0)
        self.donation_individual = kwargs.get("donation_individual", False)
        self.donation_group = kwargs.get("donation_group", False)
        self.donation_ingroup = kwargs.get("donation_ingroup", False)
        self.donation_public = kwargs.get("donation_public", False)
        self.intergroup_competition = kwargs.get("intergroup_competition", 1)
        self.intragroup_competition = kwargs.get("intragroup_competition", 1)
        self.score_visible = kwargs.get("score_visible", False)
        self.alternate_consumption_donation = kwargs.get(
            "alternate_consumption_donation", False
        )

        # Chat
        self.chat_message_history = []

        # Questionnaire
        self.difi_question = kwargs.get("difi_question", False)
        self.difi_group_label = kwargs.get("difi_group_label", "Group")
        self.difi_group_image = kwargs.get(
            "difi_group_image", "/static/images/group.jpg"
        )
        self.fun_survey = kwargs.get("fun_survey", False)
        self.pre_difi_question = kwargs.get("pre_difi_question", False)
        self.pre_difi_group_label = kwargs.get("pre_difi_group_label", "Group")
        self.pre_difi_group_image = kwargs.get(
            "pre_difi_group_image", "/static/images/group.jpg"
        )
        self.leach_survey = kwargs.get("leach_survey", False)

        # Set some variables.
        self.players = {}
        self.item_locations = {}
        self.items_consumed = []
        self.start_timestamp = kwargs.get("start_timestamp", None)

        self.round = 0

        if self.contagion_hierarchy:
            self.contagion_hierarchy = range(self.num_colors)
            random.shuffle(self.contagion_hierarchy)

        if self.costly_colors:
            self.color_costs = [2**i for i in range(self.num_colors)]
            random.shuffle(self.color_costs)

        # Items and transitions
        self.item_config = kwargs.get("item_config", DEFAULT_ITEM_CONFIG)
        self.transition_config = kwargs.get("transition_config", {})

        # Any maturing items?
        self.includes_maturing_items = any(
            item["maturation_threshold"] > 0.0 for item in self.item_config.values()
        )

        # Get item spawning probability distribution function and args
        for item_type in self.item_config.values():
            item_type["probability_function_args"] = []
            parts = item_type["probability_distribution"].split()
            if len(parts) > 1:
                item_type["probability_distribution"] = parts[0]
                item_type["probability_function_args"] = parts[1:]
            probability_distribution = "{}_probability_distribution".format(
                item_type["probability_distribution"]
            )
            item_type["probability_function"] = getattr(
                distributions, probability_distribution, None
            )
            if item_type["probability_function"] is None:
                logger.info(
                    "Unknown item probability distribution: {}.".format(
                        item_type["probability_distribution"]
                    )
                )
                item_type[
                    "probability_function"
                ] = distributions.random_probability_distribution

        # public good
        for item_type in self.item_config.values():
            item_type["public_good"] = (
                item_type["calories"]
                * item_type["public_good_multiplier"]
                / self.num_players
            )

    def can_occupy(self, position):
        if self.player_overlap:
            return not self.has_wall(position)
        return not self.has_player(position) and not self.has_wall(position)

    @property
    def limited_player_colors(self):
        return self.player_colors[: self.num_colors]

    @property
    def limited_player_color_names(self):
        return self.player_color_names[: self.num_colors]

    @property
    def elapsed_round_time(self):
        if self.start_timestamp is None:
            return 0
        return time.time() - self.start_timestamp

    @property
    def remaining_round_time(self):
        if self.start_timestamp is None:
            return 0
        raw_remaining = self.time_per_round - self.elapsed_round_time

        return max(0, raw_remaining)

    @property
    def group_donation_enabled(self):
        return self.donation_group or self.donation_ingroup

    @property
    def donation_enabled(self):
        return (
            self.group_donation_enabled
            or self.donation_individual
            or self.donation_public
        ) and bool(self.donation_amount)

    @property
    def is_even_round(self):
        return bool(self.round % 2)

    @property
    def donation_active(self):
        """Donation is enabled if:
        1. at least one of the donation_individual, donation_group and
           donation_public flags is set to True
        2. donation_amount to some non-zero value

        Further, donation is limited to even-numbered rounds if
        alternate_consumption_donation is set to True.
        """
        if not self.donation_enabled:
            return False

        if self.alternate_consumption_donation:
            return self.is_even_round

        return True

    @property
    def movement_enabled(self):
        """If we're alternating consumption and donation, Players can only move
        during consumption rounds.
        """
        if self.alternate_consumption_donation and self.donation_active:
            return False
        return True

    @property
    def consumption_active(self):
        """Food consumption is enabled on odd-numbered rounds if
        alternate_consumption_donation is set to True.
        """
        return not self.alternate_consumption_donation or not self.is_even_round

    def players_with_color(self, color_id):
        """Return all the players with the specified color, which is how we
        represent group/team membership.
        """
        color_id = int(color_id)
        return [p for p in self.players.values() if p.color_idx == color_id]

    def check_round_completion(self):
        if not self.game_started:
            return

        if not self.remaining_round_time:
            self.round += 1
            if self.game_over:
                return

            self.start_timestamp = time.time()
            # Delay round for leaderboard display
            if self.leaderboard_individual or self.leaderboard_group:
                self.start_timestamp += self.leaderboard_time
            for player in self.players.values():
                player.motion_timestamp = 0

    def compute_payoffs(self):
        """Compute payoffs from scores.

        A player's payoff in the game can be expressed as the product of four
        factors: the grand total number of points earned by all players, the
        (softmax) proportion of the total points earned by the player's group,
        the (softmax) proportion of the group's points earned by the player,
        and the number of dollars per point.

        Softmaxing the two proportions implements intragroup and intergroup
        competition. When the parameters are 1, payoff is proportional to what
        was scored and so there is no extrinsic competition. Increasing the
        temperature introduces competition. For example, at 2, a pair of groups
        that score in a 2:1 ratio will get payoff in a 4:1 ratio, and therefore
        it pays to be in the highest-scoring group. The same logic applies to
        intragroup competition: when the temperature is 2, a pair of players
        within a group that score in a 2:1 ratio will get payoff in a 4:1
        ratio, and therefore it pays to be a group's highest-scoring member.
        """
        players = self.players.values()
        player_groups = {}
        total_payoff = 0
        group_scores = []
        for p in players:
            group_info = player_groups.setdefault(
                p.color_idx, {"players": [], "scores": [], "total": 0}
            )
            group_info["players"].append(p)
            group_info["scores"].append(p.score)
            group_info["total"] += p.score
            total_payoff += p.score

        for g in range(len(self.player_colors)):
            group_info = player_groups.get(g)
            if not group_info:
                group_scores.append(0)
                continue
            ingroup_players = group_info["players"]
            ingroup_scores = group_info["scores"]
            group_scores.append(group_info["total"])
            intra_proportions = softmax(
                ingroup_scores,
                temperature=self.intragroup_competition,
            )
            for i, player in enumerate(ingroup_players):
                player.payoff = total_payoff * intra_proportions[i]

        inter_proportions = softmax(
            group_scores,
            temperature=self.intergroup_competition,
        )
        for player in players:
            player.payoff *= inter_proportions[player.color_idx]
            player.payoff *= self.dollars_per_point

    def build_labyrinth(self):
        if self.walls_density and not self.wall_locations:
            start = time.time()
            logger.info("Building labyrinth:")
            walls = labyrinth(
                columns=self.columns,
                rows=self.rows,
                density=self.walls_density,
                contiguity=self.walls_contiguity,
            )
            logger.info(
                "Built {} walls in {} seconds.".format(len(walls), time.time() - start)
            )
            self.wall_locations = {tuple(w.position): w for w in walls}

    def _start_if_ready(self):
        # Don't start unless we have a least one player
        if self.players and not self.game_started:
            self.start_timestamp = time.time()

    @property
    def game_started(self):
        return self.start_timestamp is not None

    @property
    def game_over(self):
        return self.round >= self.num_rounds

    def serialize(self, include_walls=True, include_items=True):
        grid_data = {
            "players": [player.serialize() for player in self.players.values()],
            "round": self.round,
            "donation_active": self.donation_active,
            "rows": self.rows,
            "columns": self.columns,
        }

        if include_walls:
            grid_data["walls"] = [w.serialize() for w in self.wall_locations.values()]
        if include_items:
            grid_data["items"] = [f.serialize() for f in self.item_locations.values()]

        return grid_data

    def deserialize(self, state):
        if self.rows != state["rows"] or self.columns != state["columns"]:
            raise ValueError(
                "State has wrong grid size ({}x{}, configured as {}x{})".format(
                    state["rows"],
                    state["columns"],
                    self.rows,
                    self.columns,
                )
            )
        self.round = state["round"]
        # @@@ can't set donation_active because it's a property
        # self.donation_active = state['donation_active']

        self.players = {}
        for player_state in state["players"]:
            player_state["color_name"] = player_state.pop("color", None)
            player = Player(
                pseudonym_locale=self.pseudonyms_locale,
                pseudonym_gender=self.pseudonyms_gender,
                grid=self,
                **player_state,
            )
            self.players[player.id] = player

        if "walls" in state:
            self.wall_locations = {}
            for wall_state in state["walls"]:
                if isinstance(wall_state, list):
                    wall_state = {"position": wall_state}
                wall = Wall(**wall_state)
                self.wall_locations[tuple(wall.position)] = wall

        if "items" in state:
            self.item_locations = {}
            for item_state in state["items"]:
                # TODO verify this works at some point!
                item_props = self.item_config[item_state["item_id"]]
                obj = Item(item_config=item_props, **item_state)
                self.item_locations[tuple(obj.position)] = obj

    def instructions(self):
        color_costs = ""
        order = ""
        text = """<p>The objective of the game is to maximize your final payoff.
            The game is played on a {g.columns} x {g.rows} grid, where each
            player occupies one block. <br><img src='static/images/gameplay.gif'
            height='150'><br>"""
        if self.window_columns < self.columns or self.window_rows < self.rows:
            text += """ The grid is viewed through a
                {g.window_columns} x {g.window_rows} window
                that moves along with your player."""
        if self.walls_density > 0:
            text += """ There are walls throughout the grid, which the players
               cannot pass through."""
            if not self.walls_visible:
                text += " However, the walls are not visible."
        if self.build_walls:
            text += """ Players can build walls at their current position using
                the 'w' key. The wall will not appear until the player has moved
                away from that position."""
            if self.wall_building_cost > 0:
                text += """ Building a wall has a cost of {g.wall_building_cost}
                    points."""
        if self.num_rounds > 1:
            text += """ The game has {g.num_rounds} rounds, each lasting
                <strong>{g.time_per_round} seconds</strong>.</p>"""
        else:
            text += (
                " The game duration is <strong>{g.time_per_round}</strong> seconds.</p>"
            )
        if self.num_players > 1:
            text += """<p>There are <strong>{g.num_players} players</strong> participating
                in the game."""
            if not self.others_visible:
                text += """ However, players cannot see each other on the
                    grid."""
            if self.num_colors > 1:
                text += """ Each player will be one of {g.num_colors} available
                    colors ({color_list})."""
                if self.mutable_colors:
                    text += " Players can change color using the 'c' key."
                    if self.costly_colors:
                        costs = [
                            "{c}, {p} points".format(c=c, p=p)
                            for p, c in zip(
                                self.color_costs, self.limited_player_color_names
                            )
                        ]
                        color_costs = "; ".join(costs)
                        text += """ Changing color has a different cost in
                            points for each color: {color_costs}."""
                if self.contagion > 0:
                    text += """ If a player enters a region of the grid where a
                    plurality of the surrounding players within {g.contagion}
                        blocks are of a different color, that player will take
                        on the color of the plurality."""
                    if self.contagion_hierarchy:
                        order = ", ".join(
                            [
                                self.limited_player_color_names[h]
                                for h in self.contagion_hierarchy
                            ]
                        )
                        text += """ However, there is a hierarchy of colors, so
                            that only players of some colors are susceptible to
                            changing color in  this way. The hierarchy, from
                            lowest to highest, is: {order}. Colors lower in the
                            hierarchy can be affected only by higher colors."""
                    if self.frequency_dependence > 0:
                        text += """ Players will get more points if their
                            color is in the majority."""
                    if self.frequency_dependence < 0:
                        text += """ Players will get more points if their
                            color is in the minority."""
        text += """</p><p>Players move around the grid using the arrow keys.
                <br><img src='static/images/keys.gif' height='60'><br>"""
        if self.player_overlap:
            text += " More than one player can occupy a block at the same time."
        else:
            text += """ A player cannot occupy a block where a player is
                already present."""
        if self.visibility < max(self.rows, self.columns):
            text += """ Players cannot see the whole grid, but only an area
                approximately {g.visibility} blocks around their current
                position."""
        text += """<p>Press the 'h' key to toggle highlighting of your player.
                <br><img src='static/images/h-toggle.gif' height='150'><p>"""
        if self.motion_auto:
            text += """ Once a player presses a key to move, the player will
                continue to move in the same direction automatically until
                another key is pressed."""
        if self.motion_cost > 0:
            text += """ Each movement costs the player {g.motion_cost}
                        {g.motion_cost:plural, point, points}."""
        if self.motion_tremble_rate > 0 and self.motion_tremble_rate < 0.4:
            text += """ Some of the time, movement will not be in the chosen
                direction, but random."""
        if self.motion_tremble_rate >= 0.4 and self.motion_tremble_rate < 0.7:
            text += """ Movement will not be in the chosen direction most of the
                time, but random."""
        if self.motion_tremble_rate >= 0.7:
            text += """ Movement commands will be ignored almost all of the time,
                and the player will move in a random direction instead."""
        text += """</p><p>Players gain points by getting to squares that have
            food on them. Each piece of food is worth x
            points. When the game starts there
            are <strong>n</strong> pieces
            of food on the grid. Food is represented by a green"""

        text += " or brown"
        text += " square: <img src='static/images/food-green.png' height='20'>"
        text += " <img src='static/images/food-brown.png' height='20'>"
        text += "<br>Food can be respawned after it is consumed."

        text += """It will appear immediately, but may not be consumable for
            some time if it has a maturation period. It will show
            up as brown initially, and then as green when it matures."""
        text += """<br>The location where the food will appear after respawning is
            is determined by the <strong>configured</strong>
            probability distribution for each item type."""
        text += " Players may be able to plant more food by pressing the spacebar."
        text += "</p>"
        if self.alternate_consumption_donation and self.num_rounds > 1:
            text += """<p> Rounds will alternate between <strong>consumption</strong> and
            <strong>donation</strong> rounds. Consumption rounds will allow for free movement
            on the grid. Donation rounds will disable movement and allow you to donate points.</p>
            """
        if self.donation_amount > 0:
            text += """<img src='static/images/donate-click.gif' height='210'><br>
            <p>It can be helpful to donate points to others.
            """
            if self.donation_individual:
                text += """ You can donate <strong>{g.donation_amount}</strong>
                {g.donation_amount:plural, point, points} to any player by clicking on
                <img src='static/images/donate-individual.png' class='donate'
                height='30'>, then clicking on their block on the grid.
                """
            if self.donation_group:
                text += """ To donate to a group, click on the
                <img src='static/images/donate-group.png' class='donate' height='30'>
                button, then click on any player with the color of the team
                you want to donate to.
                """
            if self.donation_public:
                text += """ The <img src='static/images/donate-public.png'
                class='donate' height='30'> button splits your donation amongst
                every player in the game (including yourself).
                """
            text += "</p>"
        if self.show_chatroom:
            text += """<p>A chatroom is available to send messages to the other
                players."""
            if self.pseudonyms:
                text += """ Player names shown on the chat window are pseudonyms.
                        <br><img src='static/images/chatroom.gif' height='150'>"""
            text += "</p>"
        if self.dollars_per_point > 0:
            text += """<p>You will receive <strong>${g.dollars_per_point}</strong> for each point
                that you score at the end of the game.</p>"""
        return formatter.format(
            text,
            g=self,
            order=order,
            color_costs=color_costs,
            color_list=", ".join(self.limited_player_color_names),
        )

    def consume(self):
        """Players consume the non-interactive items"""
        consumed = 0
        for player in self.players.values():
            position = tuple(player.position)
            if position in self.item_locations:
                item = self.item_locations[position]
                if item.interactive or not item.calories:
                    continue
                if item.maturity < item.maturation_threshold:
                    continue
                del self.item_locations[position]
                # Update existence and count of item.
                self.items_consumed.append(item)
                self.items_updated = True
                if item.respawn:
                    # respawn same type of item.
                    self.spawn_item(item_id=item.item_id)
                else:
                    self.item_config[item.item_id]["item_count"] -= 1

                # Update scores.
                if player.color_idx > 0:
                    calories = item.calories
                else:
                    calories = item.calories * self.relative_deprivation

                player.score += calories
                consumed += 1

        if consumed and item.public_good:
            for player_to in self.players.values():
                player_to.score += item.public_good * consumed

    def spawn_item(self, position=None, item_id=None):
        """Respawn an item for a single position"""
        if not item_id:
            # No specific item type, pick randomly.
            item_id = None
            while item_id is None:
                # As many loops as it takes until one is chosen.
                for obj in self.item_config.values():
                    spawn_rate = random.random()
                    if spawn_rate < obj.get("spawn_rate", 0.1):
                        item_id = obj.get("item_id", 1)

        if not position:
            position = self._random_empty_position(item_id)

        item_props = self.item_config[item_id]
        new_item = Item(
            id=(len(self.item_locations) + len(self.items_consumed)),
            position=position,
            item_config=item_props,
        )
        self.item_locations[tuple(position)] = new_item
        self.items_updated = True
        logger.warning(f"Spawning new item: {new_item}")
        self.log_event(
            {
                "type": "spawn item",
                "position": position,
            }
        )

    def locations_of_item_of_type(self, item_id):
        """Return"""
        return {k: v for k, v in self.item_locations.items() if v.item_id == item_id}

    def items_changed(self, last_items):
        locations = self.item_locations
        if len(last_items) != len(locations):
            return True
        for item in last_items:
            position = tuple(item["position"])
            if position not in locations:
                return True
            found = locations[position]
            if found.id != item["id"] or found.maturity != item["maturity"]:
                return True
        return False

    def replenish_items(self):
        for item_type in self.item_config.values():
            # Alternate positive and negative growth rates
            seasonal_growth = item_type["seasonal_growth_rate"] ** (
                -1 if self.round % 2 else 1
            )
            logger.warning(
                f"item_type: {item_type['name']}, seasonal_growth: {seasonal_growth}"
            )
            # Compute how many items of this type we should have on the grid,
            # ensuring it's not less than zero.
            item_type["item_count"] = max(
                min(
                    item_type["item_count"] * item_type["spawn_rate"] * seasonal_growth,
                    self.rows * self.columns,
                ),
                0,
            )
            logger.warning(
                f"item_type: {item_type['name']}, target count: {item_type['item_count']}"
            )

            # Only items of the same type.
            item_locations = self.locations_of_item_of_type(item_type["item_id"])

            for i in range(int(round(item_type["item_count"]) - len(item_locations))):
                self.spawn_item(item_id=item_type["item_id"])

            for i in range(len(item_locations) - int(round(item_type["item_count"]))):
                del self.item_locations[random.choice(list(item_locations.keys()))]
                self.items_updated = True

    def spawn_player(self, id=None, **kwargs):
        """Spawn a player."""
        # For player position, use same distribution as first configured item.
        item_id = list(self.item_config.keys())[0]
        player = Player(
            id=id,
            position=self._random_empty_position(item_id),
            num_possible_colors=self.num_colors,
            motion_speed_limit=self.motion_speed_limit,
            motion_cost=self.motion_cost,
            score=self.initial_score,
            motion_tremble_rate=self.motion_tremble_rate,
            pseudonym_locale=self.pseudonyms_locale,
            pseudonym_gender=self.pseudonyms_gender,
            grid=self,
            identity_visible=(
                not self.identity_signaling or self.identity_starts_visible
            ),
            **kwargs,
        )
        self.players[id] = player
        self._start_if_ready()
        return player

    def _random_empty_position(self, item_id):
        """Select an empty cell at random, using the configured probability
        distribution."""
        rows = self.rows
        columns = self.columns
        empty_cell = False
        while not empty_cell:
            position = self.item_config[item_id]["probability_function"](
                rows, columns, *self.item_config[item_id]["probability_function_args"]
            )
            empty_cell = self._empty(position)

        return position

    def _empty(self, position):
        """Determine whether a particular cell is empty."""
        return not (
            self.has_player(position)
            or self.has_item(position)
            or self.has_wall(position)
        )

    def has_player(self, position):
        for player in self.players.values():
            if player.position == position:
                return True
        return False

    def has_item(self, position):
        return tuple(position) in self.item_locations

    def has_wall(self, position):
        return tuple(position) in self.wall_locations

    def spread_contagion(self):
        """Spread contagion."""
        color_updates = []
        for player in self.players.values():
            colors = [n.color for n in player.neighbors(d=self.contagion)]
            if colors:
                colors.append(player.color)
                plurality_color = max(colors, key=colors.count)
                if colors.count(plurality_color) > len(colors) / 2.0:
                    if self.rank(plurality_color) <= self.rank(player.color):
                        color_updates.append((player, plurality_color))

        for player, color in color_updates:
            player.color = color

    def rank(self, color):
        """Where does this color fall on the color hierarchy?"""
        if self.contagion_hierarchy:
            return self.contagion_hierarchy[Gridworld.player_colors.index(color)]
        else:
            return 1


@dataclass(frozen=True)
class Item:
    """A generic object supporting configuration via a game_config.yml
    definition.

    All instances sharing an item_id will share a reference to the same
    item_config, and values will be looked up from this common key/value map.
    Only values that vary by instance will be stored on the object itself.
    """
    item_config: dict
    id: int = field(default_factory=lambda: uuid.uuid4())
    creation_timestamp: float = field(default_factory=time.time)
    position: tuple = (0, 0)

    def __post_init__(self):
        object.__setattr__(self, "item_id", self.item_config["item_id"])

    def __getattr__(self, name):
        # Look up value from the item type's shared definition.
        return self.item_config[name]

    def __repr__(self):
        return (
            f"Item(name='{self.name}', item_id={self.item_id}, id={self.id}, "
            f"position={self.position}, creation_timestamp={self.creation_timestamp})"
        )

    def serialize(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "position": self.position,
            "maturity": self.maturity,
            "creation_timestamp": self.creation_timestamp,
        }

    @property
    def maturity(self):
        return round(1 - math.exp(-self._age * self.maturation_speed), 1)

    @property
    def _age(self):
        return time.time() - self.creation_timestamp


class IllegalMove(Exception):
    """A move sent from a client was denied by the server."""

    def __init__(self, message=""):
        self.message = message


class Player(object):
    """A player."""

    def __init__(self, **kwargs):
        super(Player, self).__init__()

        self.id = kwargs.get("id", uuid.uuid4())
        self.position = kwargs.get("position", [0, 0])
        self.motion_auto = kwargs.get("motion_auto", False)
        self.motion_direction = kwargs.get("motion_direction", "right")
        self.motion_speed_limit = kwargs.get("motion_speed_limit", 8)
        self.num_possible_colors = kwargs.get("num_possible_colors", 2)
        self.motion_cost = kwargs.get("motion_cost", 0)
        self.motion_tremble_rate = kwargs.get("motion_tremble_rate", 0)
        self.grid = kwargs.get("grid", None)
        self.score = kwargs.get("score", 0)
        self.payoff = kwargs.get("payoff", 0)
        self.pseudonym_locale = kwargs.get("pseudonym_locale", "en_US")
        self.identity_visible = kwargs.get("identity_visible", True)
        self.recruiter_id = kwargs.get("recruiter_id", "")
        self.add_wall = None

        # Determine the player's color. We don't have access to the specific
        # gridworld we are running in, so we can't use the `limited_` variables
        # We just find the index in the master list. This means it is possible
        # to explicitly instantiate a player with an invalid colour, but only
        # intentionally.
        if "color" in kwargs:
            self.color_idx = Gridworld.player_colors.index(kwargs["color"])
        elif "color_name" in kwargs:
            self.color_idx = Gridworld.player_color_names.index(kwargs["color_name"])
        else:
            self.color_idx = random.randint(0, self.num_possible_colors - 1)

        self.color_name = Gridworld.player_color_names[self.color_idx]
        self.color = Gridworld.player_color_names[self.color_idx]

        # Determine the player's profile.
        self.fake = Factory.create(self.pseudonym_locale)
        self.profile = self.fake.simple_profile(
            sex=kwargs.get("pseudonym_gender", None)
        )
        self.name = kwargs.get("name", self.profile["name"])
        self.username = self.profile["username"]
        self.gender = self.profile["sex"]
        self.birthdate = self.profile["birthdate"]

        self.motion_timestamp = 0
        self.last_timestamp = 0

    def tremble(self, direction):
        """Change direction with some probability."""
        directions = ["up", "down", "left", "right"]
        directions.remove(direction)
        direction = random.choice(directions)
        return direction

    def move(self, direction, tremble_rate=None, timestamp=None):
        """Move the player."""

        if not self.grid.movement_enabled:
            return

        if tremble_rate is None:
            tremble_rate = self.motion_tremble_rate

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
        if self.motion_speed_limit <= 0:
            waited_long_enough = True
        else:
            wait_time = 1.0 / self.motion_speed_limit
            if timestamp is None:
                elapsed = self.grid.elapsed_round_time
                waited_long_enough = elapsed > (self.motion_timestamp + wait_time)
            else:
                waited_long_enough = timestamp > (self.last_timestamp + wait_time)
        can_afford_to_move = self.score >= self.motion_cost

        if not waited_long_enough:
            raise IllegalMove("Minimum wait time has not passed since last move!")
        if not can_afford_to_move:
            raise IllegalMove("Not enough points to move right now!")
        if not self.grid.can_occupy(new_position):
            raise IllegalMove("Position {} not open!".format(new_position))

        msgs = {"direction": direction}
        self.position = new_position
        self.motion_timestamp = self.grid.elapsed_round_time
        if timestamp:
            self.last_timestamp = timestamp
        self.score -= self.motion_cost

        # now that player moved, check if wall needs to be built
        if self.add_wall is not None:
            new_wall = Wall(position=self.add_wall)
            self.grid.wall_locations[tuple(new_wall.position)] = new_wall
            self.add_wall = None
            wall_msg = {"type": "wall_built", "wall": new_wall.serialize()}
            msgs["wall"] = wall_msg

        return msgs

    def is_neighbor(self, player, d=1):
        """Determine whether other player is adjacent."""
        manhattan_distance = abs(self.position[0] - player.position[0]) + abs(
            self.position[1] - player.position[1]
        )
        return manhattan_distance <= d

    def neighbors(self, d=1):
        """Return all adjacent players."""
        if self.grid is None:
            return []
        return [
            p
            for p in self.grid.players.values()
            if (self.is_neighbor(p, d=d) and (p is not self))
        ]

    def serialize(self):
        return {
            "id": self.id,
            "position": self.position,
            "score": self.score,
            "payoff": self.payoff,
            "color": self.color,
            "motion_auto": self.motion_auto,
            "motion_direction": self.motion_direction,
            "motion_speed_limit": self.motion_speed_limit,
            "motion_timestamp": self.motion_timestamp,
            "name": self.name,
            "identity_visible": self.identity_visible,
            "recruiter_id": self.recruiter_id,
        }


def fermi(beta, p1, p2):
    """The Fermi function from statistical physics."""
    return 2.0 * ((1.0 / (1 + math.exp(-beta * (p1 - p2)))) - 0.5)


extra_routes = flask.Blueprint(
    "extra_routes", __name__, template_folder="templates", static_folder="static"
)


@extra_routes.route("/consent")
def consent():
    """Return the consent form. Here for backwards-compatibility with 2.x."""
    config = get_config()
    return flask.render_template(
        "consent.html",
        hit_id=flask.request.args["hit_id"],
        assignment_id=flask.request.args["assignment_id"],
        worker_id=flask.request.args["worker_id"],
        mode=config.get("mode"),
    )


@extra_routes.route("/grid")
def serve_grid():
    """Return the game stage."""
    config = get_config()
    return flask.render_template("grid.html", app_id=config.get("id"))


class Griduniverse(Experiment):
    """Define the structure of the experiment."""

    channel = "griduniverse_ctrl"
    state_count = 0
    replay_path = "/grid"

    def __init__(self, session=None):
        """Initialize the experiment."""
        self.config = get_config()
        super(Griduniverse, self).__init__(session)
        self.experiment_repeats = 1
        self.redis_conn = db.redis_conn
        if session:
            self.setup()
            self.grid = Gridworld(
                log_event=self.record_event,
                item_config=self.item_config,
                transition_config=self.transition_config,
                **self.config.as_dict(),
            )
            self.session.commit()

    def configure(self):
        super(Griduniverse, self).configure()
        self.num_participants = self.config.get("max_participants", 3)
        self.quorum = self.num_participants
        self.initial_recruitment_size = self.config.get(
            "num_recruits", self.num_participants
        )
        self.network_factory = self.config.get("network", "FullyConnected")

        game_config_file = os.path.join(os.path.dirname(__file__), GAME_CONFIG_FILE)
        with open(game_config_file, "r") as game_config_stream:
            self.game_config = yaml.safe_load(game_config_stream)
        self.item_config = {o["item_id"]: o for o in self.game_config.get("items", ())}

        # If any item is missing a key, add it with default value.
        item_defaults = self.game_config.get("item_defaults", {})
        for item in self.item_config.values():
            for prop in item_defaults:
                if prop not in item:
                    item[prop] = item_defaults[prop]

        self.transition_config = {
            (t["actor_start"], t["target_start"]): t
            for t in self.game_config.get("transitions", ())
        }
        # This is accessed by the grid.html template to load the configuration on the client side:
        # TODO: could this instead be passed as an arg to the template in
        # the /grid route?
        self.item_config_json = json.dumps(self.item_config)
        self.transition_config_json = json.dumps(
            {"{}_{}".format(k[0], k[1]): v for k, v in self.transition_config.items()}
        )

    @classmethod
    def extra_parameters(cls):
        config = get_config()
        for key in GU_PARAMS:
            config.register(key, GU_PARAMS[key])

    @property
    def environment(self):
        environment = self.socket_session.query(dallinger.nodes.Environment).one()
        return environment

    @cached_property
    def socket_session(self):
        from dallinger.db import db_url

        engine = create_engine(db_url, pool_size=1000)
        session = scoped_session(
            sessionmaker(autocommit=False, autoflush=True, bind=engine)
        )
        return session

    @property
    def background_tasks(self):
        if self.config.get("replay", False):
            return []
        return [
            self.send_state_thread,
            self.game_loop,
        ]

    def create_network(self):
        """Create a new network by reading the configuration file."""
        class_ = getattr(dallinger.networks, self.network_factory)
        return class_(max_size=self.num_participants + 1)

    def create_node(self, participant, network):
        try:
            return dallinger.models.Node(network=network, participant=participant)
        finally:
            if not self.networks(full=False):
                # If there are no spaces left in our networks we can close
                # recruitment, to alleviate problems of over-recruitment
                self.recruiter().close_recruitment()

    def setup(self):
        """Setup the networks."""
        self.node_by_player_id = {}
        if not self.networks():
            super(Griduniverse, self).setup()
            for net in self.networks():
                env = dallinger.nodes.Environment(network=net)
                self.session.add(env)
        self.session.commit()

    def serialize(self, value):
        return json.dumps(value)

    def recruit(self):
        self.recruiter().close_recruitment()

    def bonus(self, participant):
        """The bonus to be awarded to the given participant.

        Return the value of the bonus to be paid to `participant`.
        """
        data = self._last_state_for_player(participant.id)
        if not data:
            return 0.0

        return float("{0:.2f}".format(data["payoff"]))

    def bonus_reason(self):
        """The reason offered to the participant for giving the bonus."""
        return (
            "Thank you for participating! You earned a bonus based on your "
            "performance in Griduniverse!"
        )

    def dispatch(self, msg):
        """Route incoming messages to the appropriate method based on message type"""
        mapping = {
            "connect": self.handle_connect,
            "disconnect": self.handle_disconnect,
        }
        if not self.config.get("replay", False):
            # Ignore these events in replay mode
            mapping.update(
                {
                    "chat": self.handle_chat_message,
                    "change_color": self.handle_change_color,
                    "move": self.handle_move,
                    "donation_submitted": self.handle_donation,
                    "plant_food": self.handle_plant_food,
                    "toggle_visible": self.handle_toggle_visible,
                    "build_wall": self.handle_build_wall,
                }
            )

        if msg["type"] in mapping:
            mapping[msg["type"]](msg)

    def send(self, raw_message):
        """Socket interface; point of entry for incoming messages.

        param raw_message is a string with a channel prefix, for example:

            'griduniverse_ctrl:{"type":"move","player_id":0,"move":"left"}'
        """
        message = self.parse_message(raw_message)
        if message is not None:
            message["server_time"] = time.time()
            self.dispatch((message))
            if "player_id" in message:
                self.record_event(message, message["player_id"])

    def parse_message(self, raw_message):
        """Strip the channel prefix off the raw message, then return
        the parsed JSON.
        """
        if raw_message.startswith(self.channel + ":"):
            body = raw_message.replace(self.channel + ":", "")
            message = json.loads(body)

            return message

    def record_event(self, details, player_id=None):
        """Record an event in the Info table."""
        session = self.socket_session
        if player_id == "spectator":
            return
        elif player_id:
            node_id = self.node_by_player_id[player_id]
            node = session.query(dallinger.models.Node).get(node_id)
        else:
            node = self.environment

        try:
            info = Event(origin=node, details=details)
        except ValueError:
            logger.info(
                "Tried to record an event after node#{} failure: {}".format(
                    node.id, details
                )
            )
            return
        session.add(info)
        session.commit()

    def publish(self, msg):
        """Publish a message to all griduniverse clients"""
        self.redis_conn.publish("griduniverse", json.dumps(msg))

    def handle_connect(self, msg):
        player_id = msg["player_id"]
        if self.config.get("replay", False):
            # Force all participants to be specatators
            msg["player_id"] = "spectator"
            if not self.grid.start_timestamp:
                self.grid.start_timestamp = time.time()
        if player_id == "spectator":
            logger.info("A spectator has connected.")
            return

        logger.info("Client {} has connected.".format(player_id))
        client_count = len(self.grid.players)
        logger.info("Grid num players: {}".format(self.grid.num_players))
        if client_count < self.grid.num_players:
            participant = self.session.query(dallinger.models.Participant).get(
                player_id
            )
            network = self.get_network_for_participant(participant)
            if network:
                logger.info("Found an open network. Adding participant node...")
                node = self.create_node(participant, network)
                self.node_by_player_id[player_id] = node.id
                self.session.add(node)
                self.session.commit()
                logger.info("Spawning player on the grid...")
                # We use the current node id modulo the number of colours
                # to pick the user's colour. This ensures that players are
                # allocated to colours uniformly.
                self.grid.spawn_player(
                    id=player_id,
                    color_name=self.grid.limited_player_color_names[
                        node.id % self.grid.num_colors
                    ],
                    recruiter_id=participant.recruiter_id,
                )
            else:
                logger.info("No free network found for player {}".format(player_id))

    def handle_disconnect(self, msg):
        logger.info("Client {} has disconnected.".format(msg["player_id"]))

    def handle_chat_message(self, msg):
        """Publish the given message to all clients."""
        message = {
            "type": "chat",
            "message": msg,
        }

        self.grid.chat_message_history.append(
            (
                self.grid.players[msg["player_id"]],
                msg["server_time"],
                msg["contents"],
            )
        )
        # We only publish if it wasn't already broadcast
        if not msg.get("broadcast", False):
            self.publish(message)

    def handle_change_color(self, msg):
        player = self.grid.players[msg["player_id"]]
        color_name = msg["color"]
        color_idx = Gridworld.player_color_names.index(color_name)
        old_color = Gridworld.player_color_names[player.color_idx]
        msg["old_color"] = old_color
        msg["new_color"] = color_name

        if player.color_idx == color_idx:
            return  # Requested color change is no change at all.

        if self.grid.costly_colors:
            if player.score < self.grid.color_costs[color_idx]:
                return
            else:
                player.score -= self.grid.color_costs[color_idx]

        player.color = msg["color"]
        player.color_idx = color_idx
        player.color_name = color_name
        message = {
            "type": "color_changed",
            "player_id": msg["player_id"],
            "old_color": old_color,
            "new_color": player.color_name,
        }
        # Put the message back on the channel
        self.publish(message)
        self.record_event(message, message["player_id"])

    def handle_move(self, msg):
        player = self.grid.players[msg["player_id"]]
        try:
            msgs = player.move(msg["move"], timestamp=msg.get("timestamp"))
        except IllegalMove:
            error_msg = {
                "type": "move_rejection",
                "player_id": player.id,
            }
            self.publish(error_msg)
        else:
            if msgs is not None:
                msg["actual"] = msgs["direction"]
                if msgs.get("wall"):
                    wall_msg = msgs.get("wall")
                    self.publish(wall_msg)
                    self.record_event(wall_msg)

    def handle_donation(self, msg):
        """Send a donation from one player to one or more other players."""
        if not self.grid.donation_active:
            return

        recipients = []
        recipient_id = msg["recipient_id"]

        if recipient_id.startswith("group:") and self.grid.group_donation_enabled:
            color_id = recipient_id[6:]
            recipients = self.grid.players_with_color(color_id)
        elif recipient_id == "all" and self.grid.donation_public:
            recipients = self.grid.players.values()
        elif self.grid.donation_individual:
            recipient = self.grid.players.get(recipient_id)
            if recipient:
                recipients.append(recipient)
        donor = self.grid.players[msg["donor_id"]]
        donation = msg["amount"]

        if donor.score >= donation and len(recipients):
            donor.score -= donation
            donated = donation * self.grid.donation_multiplier
            if len(recipients) > 1:
                donated = round(donated / len(recipients), 2)
            for recipient in recipients:
                recipient.score += donated
            message = {
                "type": "donation_processed",
                "donor_id": msg["donor_id"],
                "recipient_id": msg["recipient_id"],
                "amount": donation,
                "received": donated,
            }
            self.publish(message)
            self.record_event(message, message["donor_id"])

    def handle_plant_food(self, msg):
        # Legacy. For now, take planting info from first defined item.
        planting_cost = list(self.item_config.values())[0]["planting_cost"]
        player = self.grid.players[msg["player_id"]]
        position = msg["position"]
        can_afford = player.score >= planting_cost
        if can_afford and not self.grid.has_item(position):
            player.score -= planting_cost
            self.grid.spawn_item(position=position)

    def handle_toggle_visible(self, msg):
        player = self.grid.players[msg["player_id"]]
        player.identity_visible = msg["identity_visible"]

    def handle_build_wall(self, msg):
        player = self.grid.players[msg["player_id"]]
        position = msg["position"]
        can_afford = player.score >= self.grid.wall_building_cost
        msg["success"] = can_afford
        if can_afford:
            player.score -= self.grid.wall_building_cost
            player.add_wall = position

    def send_state_thread(self):
        """Publish the current state of the grid and game"""
        count = 0
        last_player_count = 0
        gevent.sleep(1.00)
        last_walls = []
        last_items = []

        # Sleep until we have walls
        while self.grid.walls_density and not self.grid.wall_locations:
            gevent.sleep(0.1)

        while True:
            gevent.sleep(self.config.get("state_interval", 0.050))

            # Send all item data once every 40 loops
            update_walls = update_items = False
            if (count % 50) == 0:
                update_items = True
            count += 1

            player_count = len(self.grid.players)
            if not last_player_count or player_count != last_player_count:
                update_walls = True
                update_items = True
                last_player_count = player_count

            if not last_walls:
                update_walls = True

            if not last_items or self.grid.items_changed(last_items):
                update_items = True

            grid_state = self.grid.serialize(
                include_walls=update_walls, include_items=update_items
            )

            if update_walls:
                last_walls = grid_state["walls"]

            if update_items:
                last_items = grid_state["items"]

            message = {
                "type": "state",
                "grid": json.dumps(grid_state),
                "count": count,
                "remaining_time": self.grid.remaining_round_time,
                "round": self.grid.round,
            }

            self.publish(message)
            if self.grid.game_over:
                return

    def game_loop(self):
        """Update the world state."""
        gevent.sleep(0.1)
        if not self.config.get("replay", False):
            self.grid.build_labyrinth()
            logger.info("Spawning items")
            for item_type in self.item_config.values():
                for i in range(item_type["item_count"]):
                    if (i % 250) == 0:
                        gevent.sleep(0.00001)
                    self.grid.spawn_item(item_id=item_type["item_id"])

        while not self.grid.game_started:
            gevent.sleep(0.01)

        previous_second_timestamp = self.grid.start_timestamp
        count = 0

        while not self.grid.game_over:
            # Record grid state to database
            state_data = self.grid.serialize(
                include_walls=self.grid.walls_updated,
                include_items=self.grid.items_updated,
            )
            state = self.environment.update(json.dumps(state_data), details=state_data)
            self.socket_session.add(state)
            self.socket_session.commit()
            count += 1
            self.grid.walls_updated = False
            self.grid.items_updated = False
            gevent.sleep(0.010)

            # TODO: Most of this code belongs in Gridworld; we're just looking
            # at properties of that class and then telling it to do things based
            # on the values.

            # Log item updates every hundred rounds to capture maturity changes
            if self.grid.includes_maturing_items and (count % 100) == 0:
                self.grid.items_updated = True
            now = time.time()

            # Update motion.
            if self.grid.motion_auto:
                for player in self.grid.players.values():
                    player.move(player.motion_direction, tremble_rate=0)

            # Consume the food.
            if self.grid.consumption_active:
                self.grid.consume()

            # Spread through contagion.
            if self.grid.contagion > 0:
                self.grid.spread_contagion()

            # Trigger time-based events.
            if (now - previous_second_timestamp) > 1.000:
                # Grow or shrink the item stores.
                self.grid.replenish_items()

                abundances = {}
                for player in self.grid.players.values():
                    # Apply tax.
                    player.score = max(player.score - self.grid.tax, 0)
                    if player.color not in abundances:
                        abundances[player.color] = 0
                    abundances[player.color] += 1

                # Apply frequency-dependent payoff.
                if self.grid.frequency_dependence:
                    for player in self.grid.players.values():
                        relative_frequency = (
                            1.0 * abundances[player.color] / len(self.grid.players)
                        )
                        payoff = (
                            fermi(
                                beta=self.grid.frequency_dependence,
                                p1=relative_frequency,
                                p2=0.5,
                            )
                            * self.grid.frequency_dependent_payoff_rate
                        )

                        player.score = max(player.score + payoff, 0)

                previous_second_timestamp = now

            self.grid.compute_payoffs()
            game_round = self.grid.round
            self.grid.check_round_completion()
            if self.grid.round != game_round and not self.grid.game_over:
                self.publish({"type": "new_round", "round": self.grid.round})
                self.record_event({"type": "new_round", "round": self.grid.round})

        self.publish({"type": "stop"})
        self.socket_session.commit()
        return

    def player_feedback(self, data):
        engagement = int(json.loads(data.questions.list[-1][-1])["engagement"])
        difficulty = int(json.loads(data.questions.list[-1][-1])["difficulty"])
        try:
            fun = int(json.loads(data.questions.list[-1][-1])["fun"])
            return engagement, difficulty, fun
        except IndexError:
            return engagement, difficulty

    def replay_start(self):
        self.grid = Gridworld(log_event=self.record_event, **self.config.as_dict())

    def replay_started(self):
        return self.grid.game_started

    def events_for_replay(self, session=None, target=None):
        info_cls = dallinger.models.Info
        from .models import Event

        # Get the base query from the parent class, but remove order_by fields as we override them
        # in the subqueries
        events = Experiment.events_for_replay(
            self, session=session, target=target
        ).order_by(False)
        if target is None:
            # If we don't have a specific target time we can't optimise some states away
            return events

        # We never care about events after the target time or before the current state
        events = events.filter(
            info_cls.creation_time <= target,
            info_cls.creation_time > self._replay_time_index,
        )

        # Get the most recent eligible update that changed the food positions
        item_events = (
            events.filter(
                info_cls.type == "state",
                Event.details["items"] != None,  # noqa: E711
            )
            .order_by(Event.creation_time.desc())
            .limit(1)
        )

        # Get the most recent eligible update that changed the wall positions
        wall_events = (
            events.filter(
                info_cls.type == "state",
                Event.details["walls"] != None,  # noqa: E711
            )
            .order_by(Event.creation_time.desc())
            .limit(1)
        )

        # Get the most recent eligible update that changed the player positions
        update_events = (
            events.filter(
                info_cls.type == "state",
                Event.details["players"] != None,  # noqa: E711
            )
            .order_by(Event.creation_time.desc())
            .limit(1)
        )

        # Get all eligible updates of the below types
        event_types = {"chat", "new_round", "donation_processed", "color_changed"}
        typed_events = events.filter(
            info_cls.type == "event", Event.details["type"].astext.in_(event_types)
        )

        # Merge the above four queries, discarding duplicates, and put them in time ascending order
        merged_events = item_events.union(
            wall_events, update_events, typed_events
        ).order_by(Event.creation_time.asc())

        # Limit the query to the type, the effective time and the JSONB field containing the data
        return merged_events.with_entities(
            info_cls.type, info_cls.creation_time, info_cls.details
        )

    def replay_event(self, event):
        if "server_time" not in event.details:
            # If we don't have a server time in the event we reconstruct it from
            # the event metadata
            event.details["server_time"] = (
                time.mktime(event.creation_time.timetuple())
                + event.creation_time.microsecond / 1e6
            )
        if event.type == "event":
            self.publish(event.details)
            if event.details.get("type") == "new_round":
                self.grid.check_round_completion()
            elif event.details.get("type") == "chat":
                self.handle_chat_message(event.details)

        if event.type == "state":
            self.state_count += 1
            state = event.details
            if not state:
                # Allow loading older exports that didn't fill the details column
                state = json.loads(event.contents)
            msg = {
                "type": "state",
                "grid": state,
                "count": self.state_count,
                "remaining_time": self.grid.remaining_round_time,
                "round": state["round"],
            }
            self.grid.deserialize(state)
            self.publish(msg)

    @property
    def usable_replay_range(self):
        # Start when the first player connects
        start_time = (
            self.import_session.query(Event)
            .filter(Event.details["type"].astext == "connect")
            .order_by(Event.creation_time)[0]
            .creation_time
        )
        # At the start of the following second, as Dallinger truncates milliseconds for start time
        start_time += datetime.timedelta(seconds=1)
        # End at the last move
        end_time = (
            self.import_session.query(Event)
            .filter(Event.details["type"].astext == "move")
            .order_by(Event.creation_time.desc())[0]
            .creation_time
        )
        return (start_time, end_time)

    def revert_to_time(self, session=None, target=None):
        self._replay_time_index = self.usable_replay_range[0] - datetime.timedelta(
            minutes=1
        )
        self.grid.chat_message_history = []
        self.state_count = 0
        self.grid.players = {}
        self.grid.item_locations = {}
        self.grid.wall_locations = {}

    def replay_finish(self):
        self.publish({"type": "stop"})

    def analyze(self, data):
        return json.dumps(
            {
                "average_payoff": self.average_payoff(data),
                "average_score": self.average_score(data),
                "number_of_actions": self.number_of_actions(data),
                "average_time_to_start": self.average_time_to_start(data),
            }
        )

    def isplit(self, seq, splitters):
        """Split a list into nested lists on a value (or tuple or list of values)
        https://stackoverflow.com/questions/4322705/split-a-list-into-nested-lists-on-a-value
        auxilary function to number_of_actions"""
        return [
            list(g)
            for k, g in itertools.groupby(seq, lambda x: x in splitters)
            if not k
        ]

    def number_of_actions_per_round(self, origin_ids, moves):
        """Calculate number of moves/player for a specific round
        auxilary function to number_of_actions"""
        player_move_data = []
        for player in origin_ids:
            players_moves = [
                x for x in moves if x[11] == player
            ]  # Get all the moves of a player
            if len(players_moves) != 0:
                player_id = json.loads(players_moves[0][9])["player_id"]
                player_move_data.append(
                    {"player_id": player_id, "total_moves": len(players_moves)}
                )
        return player_move_data

    def number_of_actions(self, data):
        """Return a dictionary containing the # of actions taken
        for each participant per round"""
        df = data.infos.df
        dataState = df.loc[df["type"] == "state"]
        if dataState.empty:
            return []
        dlist = data.infos.list
        moves_and_round_breaks = [
            x
            for x in dlist
            if x[10] == "event" and ("move" in x[9] or "new_round" in x[9])
        ]
        # Find all the round dividers/breaks
        round_breaks = [x for x in moves_and_round_breaks if "new_round" in x[9]]

        # Get the unique origin_id for each player to differentiate players
        moves = [x for x in moves_and_round_breaks if "move" in x[9]]
        origin_ids = [set(x[11] for x in moves)][0]

        # Split the move data of entire game into lists containing move data for each round
        rounds_moves = self.isplit(moves_and_round_breaks, round_breaks)

        # Parse each rounds moves, one at a time
        round_number = 1
        number_of_actions_data = []
        for moves in rounds_moves:
            # Note that the round number might not match how griduniverse numbers the rounds
            # However the system used here to # rounds is verified to be accurate chronologically
            # Round 1 happened before round 2 etc
            data_dict = {
                "round_number": round_number,
                "round_data": self.number_of_actions_per_round(origin_ids, moves),
            }
            number_of_actions_data.append(data_dict)
            round_number += 1

        return number_of_actions_data

    def average_time_to_start(self, data):
        """The average time to start the game.
        Compare the time of participant's first move info to the network creation timr
        """
        df = data.infos.df
        dataState = df.loc[df["type"] == "state"]
        if dataState.empty:
            return str(datetime.timedelta(0))
        network_creation_time = data.networks.list[0][1]
        dlist = data.infos.list
        moves = [x for x in dlist if x[10] == "event" and "move" in x[9]]

        # Get the unique origin_id for each player to differentiate players
        origin_ids = set(x[11] for x in moves)

        deltasum = datetime.timedelta(0)  # init
        delta_count = 0
        for player in origin_ids:
            players_moves = [
                x for x in moves if x[11] == player
            ]  # get all the moves of a player
            if len(players_moves) != 0:  # Is it possible that the player does not move?
                # Use the time of their first move
                delta = players_moves[0][1] - network_creation_time
                delta_count += 1
                # Add up the time diffs
                deltasum += delta

        # Divide by number of players that moved (which should match the # of players present)
        if delta_count != 0:
            return str(deltasum / delta_count)
        return str(deltasum)  # in case nobody moved

    def average_payoff(self, data):
        df = data.infos.df
        dataState = df.loc[df["type"] == "state"]
        if dataState.empty:
            return 0.0
        final_state = json.loads(dataState.iloc[-1][-1])
        players = final_state["players"]
        payoff = [player["payoff"] for player in players]
        return float(sum(payoff)) / len(payoff)

    def average_score(self, data):
        df = data.infos.df
        dataState = df.loc[df["type"] == "state"]
        if dataState.empty:
            return 0.0
        final_state = json.loads(dataState.iloc[-1][-1])
        players = final_state["players"]
        scores = [player["score"] for player in players]
        return float(sum(scores)) / len(scores)

    def _last_state_for_player(self, player_id):
        most_recent_grid_state = self.environment.state()
        if most_recent_grid_state is not None:
            players = json.loads(most_recent_grid_state.contents)["players"]
            id_matches = [p for p in players if int(p["id"]) == player_id]
            if id_matches:
                return id_matches[0]

    def is_complete(self):
        """Don't consider the experiment finished until all initial
        recruits have completed the experiment."""
        finished_count = (
            self.session.query(dallinger.models.Participant)
            .filter(dallinger.models.Participant.status.in_(["approved", "rejected"]))
            .with_entities(func.count(dallinger.models.Participant.id))
            .scalar()
        )

        return finished_count >= self.initial_recruitment_size
