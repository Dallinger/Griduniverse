.. currentmodule:: dlgr.griduniverse.bots

Writing new bots
================

The best way to create a new bot strategy is create a new subclass of :class:`dlgr.griduniverse.bots.BaseGridUniverseBot` class and implement a `get_next_key` method. This allows for using the various helper functions that interpret the state of the grid.

The most important functions are :meth:`dlgr.griduniverse.bots.BaseGridUniverseBot.food_positions`, :meth:`dlgr.griduniverse.bots.BaseGridUniverseBot.player_positions` and :meth:`dlgr.griduniverse.bots.BaseGridUniverseBot.distance`. 

Unless you override the participate method, a GridUniverse bot will move approximately every second. The movement is entirely determined by the `get_next_key` method. Some bots may store state between invocations of `get_next_key` but this is not mandatory. 

.. note ::
    New bots must be added in the file `bots.py` and can be accessed by setting the `bot_policy` configuration variable to be the name of the class representing the new bot.

Example implementations
-----------------------

The most complete example is the :class:`dlgr.griduniverse.bots.AdvantageSeekingBot` bot, which stores state between invocations of :meth:`dlgr.griduniverse.bots.AdvantageSeekingBot.get_next_key` only as an optimization. The design decisions in this bot make it a good basis for writing more complex bots.

The simplest is the :class:`dlgr.griduniverse.bots.RandomBot` which behaves purely randomly, so likely is not a good model for new bots.

Other potential strategies
--------------------------

There are many different strategies that can be implemented for bots in GridUniverse. The `AdvantageSeekingBot` is a good example of one strategy, but two others are listed here in the hope that authors of strategies may find the approach they take instructive.

Exploration and local detours
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Some GridUniverse games run with a small visible window. To emulate the behavior of real humans in this scenario you may choose to move around the grid exploring then detouring when food is visible.

This could be performed by storing state about the last time a piece of food was seen and moving between random corners when no food is known, for example:

.. code-block:: python

    def __init__(self, *args, **kwargs):
        ...
        self.target = None

    def get_next_key(self):
        if self.target == self.my_position:
            # Clear the target once we reach it
            self.target = None

        if self.target is None:
            self.target = random.choice([
                (0, self.state['rows']),
                (self.state['columns'], self.state['rows']),
                (self.state['columns'], 0),
                (0, 0),
            ])

            while self.target in self.wall_positions:
                # The target is a wall, pick randomly until we find a reachable target
                self.target = (
                    random.randint(0, self.state['columns']),
                    random.randint(0, self.state['rows'])
                )

        for coordinate in self.food_positions:
            if self.manhattan_distance(self.my_position, coordinate) < 10:
                # This piece of food is visible, move towards that instead
                self.target = coordinate

        # Get the best route to the target and return the first key
        distance, directions = self.distance(self.my_position, self.target)
        if distance is None:
            # This target is no longer reachable, try again next time we need a key
            self.target = None
            return ""
        else:
            return directions[0]
        
There are four distinct phases to this example: 

1. The bot checks to see if it has reached its stored objective. If it has, it clears the objective ready to set another. 
2. If there is no stored objective, the bot attempts to set the target to a corner of the grid, or a random place if that is not a valid location
3. The bot checks to see if there are any piece of food within 10 squares of its  location, according to the manhattan distance. This is an approximation for things being visible to human players. If there are any food items within range they will be set as the target.
4. The bot finds the best route to the current target. If the target is not routable then it is unset and no movement is performed, otherwise the first step of the movement is performed.

There are many ways this strategy could be improved, both for realism and code runtime, but it gives a simple view of a stateful bot that behaves in a useful way.

Balanced random movement
^^^^^^^^^^^^^^^^^^^^^^^^

An improvement on the random bot could be that it should move randomly but in such a way that it prefers moving to squares it has visited less. This strategy does not take any food locations into account, but does have net movement, unlike the purely random bot.


.. code-block:: python

    def __init__(self, *args, **kwargs):
        ...
        self.past_locations = collections.Counter()

    def get_next_key(self):
        self.past_locations[self.my_position] += 1
        positions = {}
        for key in {Keys.UP, Keys.DOWN, Keys.LEFT, Keys.RIGHT}:
            # Set up a mapping of possible direction to how many times we visited that square
            expected_position = self.get_expected_position(key)[self.player_id]
            positions[key] = self.past_locations[expected_position]
        
        while len(positions) > 1:
            # To get an simple weighted random number, we iteratively exclude keys weighted
            # by how often we visited their targets.
            # For example, if we have {UP: 0, DOWN: 1, LEFT: 10, RIGHT: 10}
            # LEFT and RIGHT are 10 times more likely than DOWN to be excluded. UP will not
            # be excluded, so will be the eventual pick in this example.
            choices = []
            for key, visits in positions.items():
                choices += [key] * visits
            exclude = random.choice(choices)
            del positions[exclude]
        
        # Return the remaining key
        return positions.keys()[0]
        
Here we keep track of state, but the state is not used to bypass decision making, rather it is used to weight future decisions.

Debugging bots
--------------

When running bots it can be quite difficult to tell if they are behaving as expected. There are two primary ways that they can be debugged. Firstly, if the bot uses the BaseGridUniverseBot base class rather than HighPerformanceBaseGridUniverseBot, the Selenium browser in use will show the current actions. This allows the developer to directly see what the bot is doing. Even if this isn't the case, the server is still running so the developer can enter the experiment as a spectator by visiting /grid.

The second broad approach is to the Python debugging tools. As Dallinger runs using multiple processes and concurrency within workers this can be difficult to achieve. Developers have had great success using the `remote-pdb` library ( https://pypi.org/project/remote-pdb/ ) especially when hard-coding a listen port, such as:

.. code-block:: python

    from remote_pdb import RemotePdb; RemotePdb('127.0.0.1', 4444).set_trace()

This allows the developer to connect using `telnet` or `nc` even if the output of the bot is entirely captured:

.. code-block:: bash

    $ nc 127.0.0.1 4444
    (Pdb) 

It is also recommended to write unit tests for the bots, to ensure that actions on known good data work as expected. There are some example tests for the built-in bots to this end.

Base class reference
--------------------

.. autoclass:: HighPerformanceBaseGridUniverseBot
  :members:

.. autoclass:: BaseGridUniverseBot
  :members:

