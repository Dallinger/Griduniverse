GridUniverse configuration parameters
=====================================

max_participants
----------------

Number of players. Default is 3.


num_rounds
----------

Number of rounds. Default is 1.


time_per_round
--------------

Time per round, in seconds. Defaults to 300.


instruct
--------

Whether to show instructions to the players or not. True by default.


columns
-------

Number of columns for the grid. Default is 25.


rows
----

Number of rows for the grid. Default is 25.


block_size
----------

Size of each side of a  block in the grid, in pixels. Defaults to 10.


padding
-------

Space between blocks, in pixels. Default is 1.


visibility
----------

How many blocks around a player are visible in the grid. Default is 1000, so
all grid is visible.


background_animation
--------------------

Play a background animation around the visible area for a player. Default is
True.


player_overlap
--------------

Whether two players can be on the same block at the same time. False by default.


motion_speed_limit
------------------

Factor to use in determining wait time between moves. Goes from 1 to 1000, where
1000 equals zero wait. Default is 16.


motion_auto
-----------

Wheter movement in the direction of previous player motion is automatic. Default
is False.


motion_cost
-----------

Cost in points for each movement. Default is 0.


motion_tremble_rate
-------------------

Rate of random direction change for player movement. From 0 to 1. a value of 0
means movement is always in the direction the player specified; a value of 1
means all movement is random.


show_chatroom
-------------

Whether the chatroom should appear in the UI. Defaults to True.


show_grid
---------

Show the grid in the UI. Defaults to True.


others_visible
--------------

Whether other players are visible on the grid. Deafult is True.


num_colors
----------

Number of possible colors for a player. Defaults to 3.


mutable_colors
--------------

Setting this to True allows players to change colors using the keyboard. False
by default.


costly_colors
-------------

Controls whether changing color has a random cost in points for each color.
Defaults to False.


pseudonyms
----------

Use generated pseudonyms instead of player numbers for chat messages. Defaults
to True.


pseudonyms_locale
-----------------

Locale for the generated pseudonyms. Defaults to en_US.


pseudonyms_gender
-----------------

Gender for the generated pseudonyms. Defaults to None.


contagion
---------

Distance from each player where a neighboring player can be "infected" and thus
become the color of its neighbor. Default is 0, so no contagion can occur.


contagion_hierarchy
-------------------

If True, assigns a random hierarchy to player colors, so that a higher color in
the hierarchy is more "contagious" than the lower color. Default is False.


walls_visible
-------------

Whether the maze walls, if any, are visible. Defaults to True.


walls_density
-------------

Defines if the grid will have a maze and how many walls it will have. A density
of 0 means no walls, while 1 means the most possible walls. Default is 0.


walls_contiguity
----------------

Whether the maze walls are contiguous or have random holes. The default, 1,
means contiguous.


initial_score
-------------

Initial score for each player. Default is 0.


dollars_per_point
-----------------

How much will be gained by each player in US dollars when the game ends.
Default is $0.02.


tax
---

Amount if points to tax each player for each second on the grid. Default is
0.01.


relative_deprivation
--------------------

When food is cosumed, multiply food reward by this factor to get total reward.
Defaults to 1.


frequency_dependence
--------------------

The value here is used to calculate a payoff to add to the players score
according to the frequency of their color. Higher values mean higher payoff. The
default is 0.


frequency_dependent_payoff_rate
-------------------------------

How big is the frequency dependent payoff. The payoff is multiplied by this
value. Default is 0.


donation
--------

Amount of donation, in points, that a player can make to another by clicking on
its color in the grid. Default is 0.


num_food
--------

Number of food blocks at game start. Default is 8.


respawn_food
------------

Whether to spawn food again after it is consumed. Defaults to True.


food_visible
------------

If True, food is visible on the grid, which is the default.


food_reward
-----------

Value in points for each block of food. Default is 1.


food_pg_multiplier
------------------

Amount to multiply for food reward to distribute among all players each time
food is cosumed. Default is 1.


food_growth_rate
----------------

Rate at which food grows every second during the game. Default is 1.


food_maturation_speed
---------------------

Speed of increase in maturity for spawned food blocks. Default is 1.


food_maturation_threshold
-------------------------

Maturity value required for food to be ready to consume. Defaults to 0.


food_planting
-------------

If True, players can plant food using the space bar. False by default.


food_planting_cost
------------------

How many points it costs for a player to plant food. Default is 1.


seasonal_growth_rate
--------------------

The rate of food store growth or shrinkage each second. Default is 1.


difi_question
-------------

Whether to ask a question at the end to help determine the Dynamic Identity
Fusion Index (DIFI) of the player. Default is False.


difi_group_label
----------------

The label to use for the group when asking the DIFI question at the end.


difi_group_image
----------------

The group image to use when asking the DIFI question at the end. 


leach_survey
------------

If true, the Leach survey is applied as part of the ending questionnaire.
Default is False.
