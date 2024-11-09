# Griduniverse

[![Build Status](https://github.com/dallinger/Griduniverse/actions/workflows/test.yml/badge.svg)](https://github.com/Dallinger/Griduniverse/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/Dallinger/Griduniverse/branch/master/graph/badge.svg)](https://codecov.io/gh/Dallinger/Griduniverse)

Reinforcement learning is an area of machine learning that considers the problem faced by a decision-maker in a setting partly under control of the environment. To illustrate the complexities of learning in even simple scenarios, researchers often turn to so-called “Gridworlds”, toy problems that nonetheless capture the rich difficulties that arise when learning in an uncertain world. By adjusting the state space (i.e., the grid), the set of actions available to the decision maker, the reward function, and the mapping between actions and states, a richly structured array of reinforcement learning problems can be generated — a Griduniverse, one might say. To design a successful reinforcement learning AI system, then, is to develop an algorithm that learns well across many such Gridworlds. Indeed, state-of-the-art reinforcement learning algorithms such as deep Q-networks, for example, have achieved professional-level performance across tens of video games from raw pixel input.

Fig. 1. A small Gridworld, reprinted from Sutton & Barto (1998). At each time step, the agent selects a move (up, down, left, right) and receives the reward specified in the grid.

Here, we create a Griduniverse for the study of human social behavior — a parameterized space of games expansive enough to capture a diversity of relevant dynamics, yet simple enough to permit rigorous analysis. We begin by documenting parameters of the Griduniverse. We then describe a broad set of existing experimental paradigms and economic games that exists as worlds in this universe. To build a successful model of collective identity formation is to create one that can explain many such worlds.

## Elements of the Griduniverse

## Grid Universe

The Grid Universe is a Dallinger Experiment. The Universe consists of multiple
Games, each of which has an initial Grid World in which players interact.

### Game

A Game runs in a single Dallinger Network, that consists of a Grid World and a
number of participants. Multiple Games can be run concurrently, and a game can
continue for multiple rounds with the same players and/or evolve into a new Grid
with a new set of players.

### Grid

A Gridworld contains a grid (GRID_HEIGHT, GRID_WIDTH). For example, Fig. 2 shows two players on a 20 × 20 grid.

Fig. 2. Two players on a 20 × 20 grid.

### Players

A set of players inhabit the Gridworld (N). Each player has a position on the grid (INITIAL_POSITION). Players may be controlled by human participants, bots, bionics, or some combination.

Players may have control over their position on the grid (IS_PLAYER_MOTION). If players can control their position, it may be in one of two ways — through actions that change the direction of always present motion, or that change the position of an otherwise motionless player (IS_MOTION_PERPETUAL). Each player has a fixed maximum speed of motion (SPEED), which may vary across players. Players may be able to move and change direction throughout the game, or there may be actions that prevent further motion (FREEZING_ACTIONS).

Players take on one of some number of distinguishable identities (NUM_IDENTITIES). Players may select their identity of it may be assigned to them (IS_IDENTITY_SELECTED). Players may be allowed to move freely between identities (IS_IDENTITY_FLUID). Players may be able to see the identity of others. Ability to see the identity of others may depend on their position on the grid, the identity of the player or the other player, or the network structure. Identities may be transmissible based on spatial proximity or network structure.

Fig. 3. Sample colors that could serve as distinguishable identities.

### Other Grid Objects

The world may contain various other non-player objects, some of which may be interactive, provide "calories" or "points", or enable players to progress through the
game in various ways, and some of which are inert and non-interactive (walls). Points contribute to the players overall score in the game.

#### Walls

Walls are labyrinth of immovable obstacles added to the grid when it's initially constructed. The density and contiguity of the labyrinth can by configured
via configuration parameters (see below).

#### Items

Griduniverse provides a rich system for defining interactive and/or nutrition-providing "items" which will also be added to the world. In addition to defining
properties of the items themselves (caloric value, whether than can be carried by players, whether they respawn automatically, etc.), experiment authors
can also define transitions that execute when players interact with the item on the block they currently occupy, potentially in combination with an item
they are carrying. For example, a player carrying a stone might be able to transform the stone into a more useful "sharp stone" by sharpening against a
"large rock" that exists in the block they currently occupy. For more details, see [Items and Transitions](#items-and-transitions) below.

### Chatroom

Players may be given a free-form chatroom that allows them to communicate with others (IS_CHATROOM). If there is a chatroom, players may be able to communicate only with those who share an identity (IS_CHAT_WITH_OTHERS), are neighbors in their social network, or are within some distance from the player (CHATROOM_MIN_DISTANCE).

### Social network

Players are situated in a social network that may determine who they can see or chat with. Players may be able to rewire the network by forging or breaking links.

### Score

Players have a score that determines their payout in the game. A players score rises and falls depending on their actions and those of others. Players may receive points based on their location, proximity to others in a network, random chance, and their interactions with others.

### Actions

Players may be able to interact with other players. For example, players may be able to transfer some or all of their score to others (IS_REWARD_OTHERS, MAX_REWARD_TO_OTHERS, IS_REWARD_TO_OTHERS_ALL_OR_NONE), and this transference may be limited by position, network structure, or identity.

### Gameplay

The game may have multiple rounds (NUM_ROUNDS). Each round may last until a particular outcome or for a given amount of time (STOPPING_RULE).

### In-game questionnaire

At various points, the game may pause and players will be asked to respond to the Dynamic Identity Fusion Index survey instrument as it pertains to a particular identity. Players may also be asked to complete a longer survey instrument. These survey instruments may also be administered at the close of the game.

### Metagame questionnaire

Players will be asked various questions that exist outside the Griduniverse. At the beginning of the study, they will be asked to consent. At the end of the study, they will be asked to answer questions about the difficulty of the game and their engagement with it.

## GridUniverse configuration parameters

### max_participants

Number of players. Default is 3.

### num_rounds

Number of rounds. Default is 1.

### num_games

Number of concurrent games to run. Default is 1.

### quorum

The number of total participants needed in the waiting room before any games can
start. Default is `max_participants`

### game_quorum

The number of participants needed in each game before the game can start. A game
can start before it has filled, any additional players will be added to the
already running game. Default is `max_participants`

### time_per_round

Time per round, in seconds. Defaults to 300.

### instruct

Whether to show instructions to the players or not. True by default.

### columns

Number of columns for the grid. Default is 25.

### rows

Number of rows for the grid. Default is 25.

### window_columns

Number of columns for the window through which the player views the grid. Default is 25.

### window_rows

Number of columns for the window through which the player views the grid. Default is 25.

### block_size

Size of each side of a block in the grid, in pixels. Defaults to 10.

### padding

Space between blocks, in pixels. Default is 1.

### visibility

The standard deviation (in blocks) of a gaussian visibility window centered on the
player. Default is 40.

### visibility_ramp_time

Controls the rate at which visibility changes as time elapses. Default is 4.

### background_animation

Play a background animation in the area visible to the player. Default is True.

### player_overlap

Whether two players can be on the same block at the same time. False by default.

### motion_speed_limit

This is the maximum speed of a player in units of blocks per second. Goes from 1
to 1000. Default is 16.

### motion_auto

Whether movement in the direction of previous player motion is automatic. This makes
the game similar to the snake game mentioned in the next section. Default is False.

### motion_cost

Cost in points for each movement. Default is 0.

### motion_tremble_rate

Rate of random direction change for player movement. From 0 to 1. A value of 0
means movement is always in the direction the player specified; a value of 1
means all movement is random.

### show_chatroom

Whether the chatroom appears in the UI. Defaults to False.

### spatial_chat

If True, chat messages will only be visible to players who can see the sender. Defaults to False.

### chat_visibility_threshold

Controls the threshold of visibility needed to see chat messages when `spatial_chat` is on.
A player's apparent dimness must be below this threshold in order for their chat messages to be seen.
Defaults to 0.4.

### show_grid

Show the grid in the UI. Defaults to True.

### others_visible

Whether other players are visible on the grid. Default is True.

### num_colors

Number of possible colors for a player. Defaults to 3.

### mutable_colors

Setting this to True allows players to change colors using the keyboard. False
by default.

### costly_colors

Controls whether changing color has a cost in points for each color. The cost
is a power of 2, starting as 2. Which color gets which cost is randomly
decided at the start of the game. Defaults to False.

### pseudonyms

Use generated pseudonyms instead of player numbers for chat messages. Defaults
to True.

### pseudonyms_locale

Locale for the generated pseudonyms. Defaults to en_US.

### pseudonyms_gender

Gender for the generated pseudonyms. Defaults to None.

### contagion

Distance from each player where a neighboring player can be "infected" and thus
become the color of the plurality of its neighbors. Default is 0, so no
contagion can occur.

### contagion_hierarchy

If True, assigns a random hierarchy to player colors, so that higher colors in
the hierarchy can spread to lower colors, but not vice versa. Default is False.

### identity_signaling

If True, a player can toggle whether or not their identity is visible to others. Defaults to False.

### identity_starts_visible

If True, a player's identity is shown when the game starts. Defaults to False.

### use_identicons

If True, players will be identified using unique icons. Defaults to False.

### walls_visible

Whether the maze walls, if any, are visible. Defaults to True.

### walls_density

Defines if the grid will have a maze and how many walls it will have. A density
of 0 means no walls, while 1 means the most possible walls. Default is 0.

### walls_contiguity

Whether the maze walls are contiguous or have random holes. The default, 1,
means contiguous.

### build_walls

Whether players can build a wall at their current position using the 'w' key. Default is False.

### wall_building_cost

The amount by which a player's score will be decreased in order to build a wall. Default is 0.

### initial_score

Initial score for each player. Default is 0.

### dollars_per_point

How much will be gained by each player in US dollars when the game ends.
Default is $0.02.

### tax

Amount of points to tax each player for each second on the grid. Default is
0.01.

### relative_deprivation

When food is consumed, multiply food reward by this factor to get total reward.
Defaults to 1.

### frequency_dependence

The value here is used to calculate a payoff to add to the player's score
according to the frequency of their color. Higher values mean higher payoff. The
default is 0.

### frequency_dependent_payoff_rate

How big is the frequency dependent payoff. The payoff is multiplied by this
value. Default is 0.

### intergroup_competition

Temperature influencing the calculation of payoffs based on competition between groups.
When the parameter is 1, payoff is proportional to what was scored and so there is no extrinsic competition. Increasing the temperature introduces competition. For example, at 2, a pair of groups that score in a 2:1 ratio will get payoff in a 4:1 ratio, and therefore it pays to be in the highest-scoring group. Default is 1.

### intragroup_competition

Temperature influencing the calculation of payoffs based on competition within groups.
When the parameter is 1, payoff is proportional to what was scored and so there is no extrinsic competition.
When the temperature is 2, a pair of players within a group that score in a 2:1 ratio will get payoff in a 4:1 ratio, and therefore it pays to be a group's highest-scoring member. Default is 1.

### leaderboard_group

Whether to show a leaderboard of group scores at the end of each round. Default is False.

### leaderboard_individual

Whether to show a leaderboard of individual scores at the end of each round. Default is False.

### leaderboard_time

How long to pause the game when showing the leaderboard, in seconds. Default is 0.

### donation_amount

Amount of donation, in points, that a player can make at a time. Default is 0.

### donation_multiplier

A donation will be multiplied by this factor to determine the number of points that will be received. Default is 1.0.

### donation_individual

Whether a player can make a donation to another individual player by clicking on their block in the grid. Default is False.

### donation_group

Whether a player can make a donation divided among a group of players by clicking on a player with that group's color. Default is False.

### donation_public

Whether a player can make a donation divided among all players in the game. Default is False.

### num_food

Number of food blocks at game start. Default is 8.

### respawn_food

Whether to spawn food again after it is consumed. Defaults to True.

### food_visible

If True, food is visible on the grid, which is the default.

### food_reward

Value in points for each block of food. Default is 1.

### food_pg_multiplier

Amount to multiply for food reward to distribute among all players each time
food is cosumed. Default is 1.

### food_growth_rate

Rate at which food grows every second during the game. Default is 1.

### food_maturation_speed

Speed of increase in maturity for spawned food blocks. Default is 1.

### food_maturation_threshold

Maturity value required for food to be ready to consume. Defaults to 0.

### food_planting

If True, players can plant food using the space bar. False by default.

### food_planting_cost

How many points it costs for a player to plant food. Default is 1.

### food_probability_distribution

By default, food is placed on the grid using a random choice from a simple
random distribution. This parameter allows the experimenter to use a
different probability distribution. Possible values are random, sinusoidal,
standing_wave, gaussian_mixture, horizontal_gradient, vertical_gradient,
edge_bias, and center_bias. The gaussian_mixture distribution takes two
optional parameters, k and sd. Other functions can take one or more
parameters as well. Parameters go after the distibution name, separated by
spaces. For example, "food_probability_distribution = gaussian_mixture 2 4".

### seasonal_growth_rate

The rate of food store growth or shrinkage each second. In odd rounds the
food store grows, and it shrinks in even rounds. Default is 1.

### difi_question

Whether to asminister the Dynamic Identity Fusion Index (DIFI) at the
end of the game. Default is False.

### difi_group_label

The label to use for the group when asking the DIFI question at the end.

### difi_group_image

URI to the group image to use when asking the DIFI question at the end. Default
is "/static/images/group.jpg".

### fun_survey

Whether to include a question on the questionnaire about how much fun the participant found the task. Default is False.

### pre_difi_question

Whether to asminister the Dynamic Identity Fusion Index (DIFI) before the
beginning of the game. Default is False.

### pre_difi_group_label

The label to use for the group when asking the DIFI question at the start.

### pre_difi_group_image

URI to the group image to use when asking the DIFI question at the start. Default
is "/static/images/group.jpg".

### leach_survey

If true, the Leach survey is applied as part of the ending questionnaire.
Default is False.

### bot_policy

Which Bot class to run. Default: `RandomBot`.

## Items and Transitions

Griduniverse provides a configuration syntax
(see [game_config.yml](./dlgr/griduniverse/game_config.yml)) for defining custom
objects that will be added to the grid world, and transitions that can be triggered by
players, either independently or in cooperation, that extract some value from the items
they're interacting with, and transform items of one type into another type. This makes
it possible for the experiment author to create pathways for techological evolution in
the game. For example, a `wild_carrot_plant` may only yield a `wild_carrot` if the
`wild_carrot` can be cut from the tree using a `sharpened_stone`, and only unsharpened
`stone`s exist in the grid world's intial state. Two players might need to collaborate
to sharpen a plain `stone` against a `big_hard_rock` to transition the `stone` into
a `sharpened_stone`, which can then be used to harvest a `wild_carrot` from the `wild_carrot_plant`.

Transitions are modeled as a pair of states: prior to the transition execution, and after
the transition has finished. Each state has two sub-componenents: the item
in the possesion of the player executing the transtion, and the item in the grid block
they are currently occupy during the transition.

Prior to transition execution:

- `actor_start` - the ID of the item the player must be holding for the transition to be available
- `target_start` - the ID of the item that must exist on the player's current grid block for the
  transition to be available

After transition execution:

- `actor_end` - the ID of the item that will exist in the player's hand after the transition
  has executed
- `target_end` - the ID of the item left in the player's grid block after the transition executes

Note that any of these values may be `null`. For example, a transition may result in the item
in the player's current grid block to be consumed, leaving nothing behind.

### Configuration

See detailed explanations for each value for items and transitions on the item_defaults
and transition_defaults definitions in [game_config.yml](./dlgr/griduniverse/game_config.yml).

## Griduniverse bots

Bots can be implemented to simulate different policies for interacting with
the Griduniverse. Currently two bot policies are implemented:

- `RandomBot`: Randomly moves in the 4 directions.
- `AdvantageSeekingBot`: Seeks an advantage by moving toward the food
  it has the biggest advantage over the other players at getting.

Dallinger configuration settings related to running bots:

- `bot_policy`: The name of the bot class to run (e.g. `RandomBot` or `AdvantageSeekingBot`).
  Defaults to `RandomBot`.
- `max_participants`: How many bots to run.
- `num_dynos_worker`: How many bot worker processes to run.
  Each process can run up to 20 bots, cooperatively multitasking using gevent.

### Bot message protocol

Bot players interact with the experiment using Redis pubsub channels.
When a bot is started it subscribes to the `griduniverse` channel and
starts listening for messages from the experiment server. When it
wants to take an action it sends a message to the `griduniverse_ctrl`
channel. Each message is a JSON-encoded object that looks like this:

    {
        "type": "chat",
        "message": "Hello bots."
    }

It contains a `type` key which designates the type of message,
and may contain other keys depending on the message type.

Positions on the grid are given in the form `[y, x]`
measuring from the top left of the grid. Colors are given in the form
`[R, G, B]` where each component is in the range 0-1.

Messages that may be received from the `griduniverse` channel are:

- `state`: Indicates the current state of the experiment.
  This message is sent repeatedly as the experiment runs.

  - `grid`: State of the grid
    - `players`: List of player info
      - `id`
      - `position`
      - `score`
      - `payoff`
      - `color`
      - `motion_auto`
      - `motion_direction`
      - `motion_speed_limit`
      - `motion_timestamp`
      - `name`
      - `identity_visible`
    - `round`: Number of the current game round
    - `donation_active`: Boolean, true if donations are enabled.
    - `rows`: Number of grid rows
    - `columns`: Number of grid columns
    - `walls`: List of wall info (not sent every time)
      - `position`
      - `color`
    - `food`: List of food info (not sent every time)
      - `id`
      - `position`
      - `maturity`
      - `color`

- `wall_built`: Reports that a wall was built.

  - `wall`:
    - `position`
    - `color`

- `color_changed`: Reports that a player's color changed.

  - `player_id`: ID of the player
  - `old_color`
  - `new_color`

- `donation_processed`: Reports that a donation of points was processed.

  - `donor_id`: ID of the donor
  - `recipient_id`: ID of a single player, OR `"all"` for a donation to all players,
    or `"group:ID"` for a donation to all players in a particular group.
  - `amount`: Number of points that were donated
  - `received`: Number of points that were received

- `chat`: A chat message from another player.

  - `player_id`: ID of the sender
  - `contents`: The message
  - `timestamp`: Time at which the message was sent
    (in milliseconds relative to the start of the experiment)

- `new_round`: Indicates the start of a new round

  - `round`: Number of the new round

- `stop`: Indicates that the game is over.

Messages that may be sent to the `griduniverse_ctrl` channel are:

- `connect`: Sent just after the bot starts listening to the `griduniverse` channel
  to let the server know that there is a new participant.

  - `participant_id`: ID of the participant
    (or `"spectator"` to receive messages without participating)

- `move`: Requests a move of one square in a given direction.

  - `player_id`: ID of the participant
  - `move`: Desired direction (up/down/left/right)
  - `timestamp`: Timestamp (in milliseconds relative to the start of the experiment)
    at which the player last moved. Optional.

- `plant_food`: Requests food to be planted at the given position.

  - `player_id`: ID of the participant
  - `position`: Coordinates [y, x]

- `build_wall`: Requests a wall to be built at the given position.

  - `player_id`: ID of the participant
  - `position`: Coordinates [y, x]

- `donation_submitted`: Requests donation of points.

  - `donor_id`: ID of the player making the donation
  - `recipient_id`: ID of a single player, OR `"all"` to donate to all players,
    or `"group:ID"` to donate to all players in a particular group.
  - `amount`: Number of points to donate

- `change_color`: Requests a change in the player's color.

  - `player_id`: ID of the participant
  - `color`: Color [R, G, B]

- `toggle_visible`: Sets visibility of the player's identity.
  - `player_id`: ID of the participant
  - `identity_visible`: Boolean indicating whether player should be visible

### Implementing a bot

Dallinger runs a bot by calling its `participate` method. A simple
`participate` method could look like this:

    def participate(self):
        self.wait_for_grid()
        self.log('Bot player started')
        while self.is_still_on_grid:
            time.sleep(self.get_wait_time())
            self.send_next_key()
        self.log('Bot player stopped.')

Let's break down what this does one step at a time:

- `self.wait_for_grid()`: Starts listening for messages,
  and sends a `connect` message indicating that the bot is present.
  Then waits until grid state has been received from the server
  and the round has started.
- `self.log('Bot player started')`: Writes an entry to the log.
- `while self.is_still_on_grid:`: Loop while there is still time remaining in the round.
- `time.sleep(self.get_wait_time())`: Waits for a randomized amount of time in between moves.
- `self.send_next_key()`: Picks a direction to move and sends a `move` message to the server.

For a bot that moves continually, use the above `participate` method
and implement a `get_next_key` method that decides which direction key
to send based on the current grid state. Note: the grid state is stored
in `self.grid` whenever a `state` message is received.

A bot can send an arbitrary message to the `griduniverse_ctrl` channel
using `self.publish(message)`.
