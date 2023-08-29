# GridUniverse Quick Start

This is a guide to get up and running with **GridUniverse** quickly. The guide assumes that you have the following software installed in your system:

 - Git.
 - Docker.
 - Python 3.8 or higher.

## Installation

The first step is to clone **GridUniverse** from the **Dallinger** `git` repository:

    $ git clone git@github.com:Dallinger/Griduniverse.git
    $ cd Griduniverse

### Create virtual Python environment
It is recommended to install all requirements into a Python virtual environment, so that your installation is self-contained and does not affect your system Python installation. To create one inside the **Griduniverse** directory, type the following:

    $ python -m venv venv

After this, you can activate the new `venv`, which will set up the shell to use all Python commands without having to add the path:

    $ source venv/bin/activate

## Running GridUniverse in development mode

Now that the environment is set up,  use `pip` from the new `venv` to install Griduniverse:

    $ pip install -e . 
    
### Starting support services

**Dallinger** experiments require a `PostgreSQL` database service to be available for saving experiment data. The easiest way to get one going is to use **Dallinger's** `Docker` support. You need to install the Python `docker` package into the`venv` first:

    $ pip install docker

Once `docker` is installed, you can launch the `PosgreSQL` service:

    $ dallinger docker start-services

To stop the services, use the following command:

    $ dallinger docker stop-services

### Running the experiment

When the services are up, You can run **GridUniverse** using its default configuration with the following command:

    $ dallinger develop debug

This will spawn initial game items according to the default game configuration (see below) and open the developer dashboard in a new browser window. Do not stop this process or the experiment will be interrupted.
Once the dashboard is open, you can test the experiment as a participant from another shell window, using the `browser` command (it might be necessary to activate the `venv` like we did in the previous section):

    $ dallinger develop browser --route ad

This will launch the experiment in a separate window. You will need to run as many browser commands as experiment participants in order for the experiment to be started.

## Modifying experiment configuration

There are two separate configuration files that can be modified to set up the experiment the way you want it.

### Dallinger `config.txt` file

This file includes general **Dallinger** configuration options. For **GridUniverse**, the most important options are:

| Option | Meaning |
|--|--|
| max_participants | Number of participants in the game |
| num_rounds | How many rounds of game play will be run |
| time_per_round | Length of each round in seconds |

### GridUniverse `game_config.yml` file

This file is well documented, so take a look at it to see the different options first. The most important high level concepts to understand the configuration are `items` and `transitions`. The easiest way to add your own game configuration is to start with the default configuration and change/copy items as needed.

#### Items
Items represent the objects available in the game. They can represent for example food, food sources, tools, or obstacles. They are the resources that the players need to obtain to get points. The most important item properties are:

| Property | Description |
|--|--|
| item_id | Each item definition must include a unique item_id. |
| item_count | How many instances of this item should the world initially include? |
| calories | How many calories does a single instance provide when a player consumes it? |
| interactive | Does a player need to explicitly interact with this item via the action button? |
| n_uses | How many times can the item be used/consumed? |
| name | Friendly name of the item that may be displayed to players. |
| portable | Whether this item be picked up and carried to another location by the player. |
| sprite | Visual representation of this item in the UI. This value can be any of a color, a Unicode emoji, or an image URL |


#### Transitions
Items are affected by `transitions`. A transition is usually initiated by a player and can change an object in various ways. For example, a rock can be turned into a tool by using a larger rock to shape it. This transition would happen when a player is holding a rock and stands on top of a large rock, producing a sharp rock that can be used as a tool. Other examples include turning a plant into an actual edible fruit or taking one fruit from a fruit tree. The most important transition properties are:
| Property | Description |
|--|--|
| actor_end | item_id for the item that will exist in the player's hand after the transition is executed. |
| actor_start | item_id for the item that must be in the player's hand in order to execute the transition. |
| target_end | item_id for the item that will exist in the player's grid block after the transition has executed. |
| target_start | item_id for the item that must exist at the player's current position in order to execute the transition |


## Deploying the experiment using Docker

To deploy the experiment you can use **Dallinger's** `Docker` support. First, add the following section to the `config.txt` file:

    [Docker]
    docker_image_base_name = ghcr.io/dallinger/dallinger/griduniverse

This will let `docker` know which image to use as a base for the experiment. You can't build an image without setting this variable.

The next step is to build the image. Make sure any `docker` services you started are stopped before proceeding. Then run the following command:

    $ dallinger docker build

Once the image is built, you can try it out on the browser with this command:

    $ dallinger docker debug

To deploy it using `MTurk` use the following command:

    $ dallinger docker deploy

