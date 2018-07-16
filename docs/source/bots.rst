.. currentmodule:: dlgr.griduniverse.bots


Bots
====

GridUniverse ships with two bots that are recognized by Dallinger.

By default, the implementations use :class:`dallinger.bots.HighPerformanceBotBase`, however they are compatible with :class:`dallinger.bots.BotBase` for easier debugging.

To run an experiment with bots it is only necessary to set the recruiter to `'bots'`. However, GridUniverse also uses a configuration variable to set the bot being used. Therefore, a simple invocation may look like:

.. code-block:: bash

    bot_policy=AdvantageSeekingBot dallinger debug --bot

however, the provided `demo.py` script provides some advantages, as it automatically analyses scoring and exports data. A typical invocation with some custom configuration is as follows:

.. code-block:: bash

    cd Griduniverse/demos
    bot_policy=AdvantageSeekingBot state_interval=0.05 num_dynos_worker=2 max_participants=2 time_per_round=160 walls_density=0.50 walls_contiguity=0.90 rows=49 columns=49 python demo.py

RandomBot
---------

The RandomBot is the simplest bot, however it is relatively unlikely to score any points. On average it will not move away from its starting position, regardless of length of game.

.. autoclass:: RandomBot
  :members:

AdvantageSeekingBot
-------------------

The AdvantageSeekingBot is significantly more complex than the RandomBot, and will likely score well compared to human players in more challenging mazes. It does not do anything more than minimal modeling of player behavior, so is more suited for mazes based on exploration than strategy.

.. autoclass:: AdvantageSeekingBot
  :members:
