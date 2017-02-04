from grid import Gridworld

from flask import abort
from flask import Flask
from flask import render_template
from flask import request
from flask_socketio import SocketIO
from jinja2 import TemplateNotFound

import math
import random
import time



socketio.start_background_task(target=game_loop)
socketio.start_background_task(target=send_state_thread)
