/*global allow_exit, create_agent, getUrlParameter, require, settings, submitResponses */

(function (allow_exit, getUrlParameter, require, reqwest, settings, submitResponses) {

var util = require("util");
var css = require("dom-css");
var grid = require("./index");
var position = require("mouse-position");
var Mousetrap = require("mousetrap");
var ReconnectingWebSocket = require("reconnecting-websocket");
var $ = require("jquery");
var gaussian = require("gaussian");

var data = [];
var background = [];
for (var i = 0; i < settings.rows; i++) {
  for (var j = 0; j < settings.columns; j++) {
    data.push([0, 0, 0]);
    background.push([0, 0, 0]);
  }
}

var PLAYER_COLORS = {
  "BLUE": [0.50, 0.86, 1.00],
  "YELLOW": [1.00, 0.86, 0.50],
  "RED": [0.64, 0.11, 0.31],
};
var GREEN = [0.51, 0.69, 0.61];
var WHITE = [1.00, 1.00, 1.00];
var CHANNEL = "griduniverse";
var CHANNEL_MARKER = CHANNEL + ":";

var pixels = grid(data, {
  rows: settings.rows,
  columns: settings.columns,
  size: settings.block_size,
  padding: settings.padding,
  background: [0.1, 0.1, 0.1],
  formatted: true
});

var mouse = position(pixels.canvas);

var library = {
  donation: {
    Frequency: {
      Start: 734.7291558862061,
      ChangeSpeed: 0.23966899924998872,
      ChangeAmount: 8.440642297186233
    },
    Volume: {
      Sustain: 0.09810917608846803,
      Decay: 0.30973154812929393,
      Punch: 0.5908451401277536
    }
  }
};

var start = Date.now();
var food = [];
var foodConsumed = [];
var walls = [];
var row, column, rand, color;

var Food = function(settings) {
  if (!(this instanceof Food)) {
    return new Food();
  }
  this.id = settings.id;
  this.position = settings.position;
  this.color = settings.color;
  return this;
};

var Wall = function(settings) {
  if (!(this instanceof Wall)) {
    return new Wall();
  }
  this.position = settings.position;
  this.color = settings.color;
  return this;
};

var Player = function(settings) {
  if (!(this instanceof Player)) {
    return new Player();
  }
  this.id = settings.id;
  this.position = settings.position;
  this.color = settings.color;
  this.motion_auto = settings.motion_auto;
  this.motion_direction = settings.motion_direction;
  this.motion_speed_limit = settings.motion_speed_limit;
  this.motion_timestamp = settings.motion_timestamp;
  this.score = settings.score;
  this.name = settings.name;
  return this;
};

Player.prototype.move = function(direction) {
  this.motion_direction = direction;

  var ts = Date.now() - start,
      waitTime = 1000 / this.motion_speed_limit;

  if (ts > this.motion_timestamp + waitTime) {
    var newPosition = this.position.slice();

    switch (direction) {
      case "up":
        if (this.position[0] > 0) {
          newPosition[0] -= 1;
        }
        break;

      case "down":
        if (this.position[0] < settings.rows - 1) {
          newPosition[0] += 1;
        }
        break;

      case "left":
        if (this.position[1] > 0) {
          newPosition[1] -= 1;
        }
        break;

      case "right":
        if (this.position[1] < settings.columns - 1) {
          newPosition[1] += 1;
        }
        break;

      default:
        console.log("Direction not recognized.");
    }
    this.motion_timestamp = ts;
  }
};

var playerSet = (function () {

    var PlayerSet = function (settings) {
        if (!(this instanceof PlayerSet)) {
            return new PlayerSet(settings);
        }

        this._players = {};
        this.ego_id = settings.ego_id;
    };


    PlayerSet.prototype.isPlayerAt = function (position) {
      var id, player;

      for (id in this._players) {
        if (this._players.hasOwnProperty(id)) {
          player = this._players[id];
          if (position === player.position) {
            return true;
          }
        } 
      }
      return false;
    };


    PlayerSet.prototype.drawToGrid = function (grid) {
      var positions = [],
          idx,
          player,
          id;

      for (id in this._players) {
        if (this._players.hasOwnProperty(id)) {
          player = this._players[id];
          if (player.motion_auto) {
            player.move(player.motion_direction);
          }
          idx = player.position[0] * settings.columns + player.position[1];
          grid[idx] = player.color;
        }
      }  
    };

    PlayerSet.prototype.nearest = function (row, column) {
      var distances = [],
                      distance,
                      player,
                      id;

      for (id in this._players) {
        if (this._players.hasOwnProperty(id)) {
          player = this._players[id];
          if (player.hasOwnProperty('position')) {
            distance = Math.abs(row - player.position[0]) + Math.abs(column - player.position[1]);
            distances.push({"player": player, "distance": distance});
          }
        }
      }

      distances.sort(function (a, b) {
        return a.distance - b.distance;
      });

      return distances[0].player;
    };

    PlayerSet.prototype.ego = function () {
      return this.get(this.ego_id);
    };  

    PlayerSet.prototype.get = function (id) {
      return this._players[id];
    }; 

    PlayerSet.prototype.update = function (playerData) {
      var currentPlayerData,
          i;

      for (i = 0; i < playerData.length; i++) {
        currentPlayerData = playerData[i];
        this._players[currentPlayerData.id] = new Player(currentPlayerData);
      }
    };

    return PlayerSet;
}());

// ego will be updated on page load
var players = playerSet({'ego_id': undefined});  

pixels.canvas.style.marginLeft = window.innerWidth * 0.03 / 2 + "px";
pixels.canvas.style.marginTop = window.innerHeight * 0.04 / 2 + "px";
document.body.style.transition = "0.3s all";
document.body.style.background = "#ffffff";


pixels.frame(function() {
  // Update the background.
  var ego = players.ego(),
      limitVisibility,
      dimness,
      rescaling,
      idx, i, j, x, y;

  for (i = 0; i < data.length; i++) {
    if (settings.background_animation) {
      rand = Math.random() * 0.02;
    } else {
      rand = 0.01;
    }
    background[i] = [
      background[i][0] * 0.95 + rand,
      background[i][1] * 0.95 + rand,
      background[i][2] * 0.95 + rand
    ];
  }

  data = background;

  for (i = 0; i < food.length; i++) {
    // Players digest the food.
    if (players.isPlayerAt(food[i].position)) {
      foodConsumed.push(food.splice(i, 1));
    } else {
      if (settings.food_visible) {
        idx = food[i].position[0] * settings.columns + food[i].position[1];
        data[idx] = food[i].color;
      }
    }
  }  

  // Draw the players:
  players.drawToGrid(data);

  // Draw the walls.
  if (settings.walls_visible) {
    walls.forEach(function(w) {
      data[w.position[0] * settings.columns + w.position[1]] = w.color;
    });
  }

  // Add the Gaussian mask.
  limitVisibility = settings.visibility <
    Math.max(settings.columns, settings.rows);
  if (limitVisibility && typeof ego !== "undefined") {
    var g = gaussian(0, Math.pow(settings.visibility, 2));
    rescaling = 1 / g.pdf(0);
    for (i = 0; i < settings.columns; i++) {
      for (j = 0; j < settings.rows; j++) {
        x = ego.position[0];
        y = ego.position[1];
        dimness = g.pdf(distance(x, y, i, j)) * rescaling;
        idx = i * settings.columns + j;
        data[idx] = [
          data[idx][0] * dimness,
          data[idx][1] * dimness,
          data[idx][2] * dimness
        ];
      }
    }
  }

  pixels.update(data);
});

function distance(x, y, xx, yy) {
  return Math.sqrt((xx - x) * (xx - x) + (yy - y) * (yy - y));
}

function arraysEqual(arr1, arr2) {
  for (var i = arr1.length; i--; ) {
    if (arr1[i] !== arr2[i]) {
      return false;
    }
  }
  return true;
}

function getRandomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function openSocket(endpoint) {
  var ws_scheme = (window.location.protocol === "https:") ? 'wss://' : 'ws://',
      app_root = ws_scheme + location.host + '/',
      socket;

  socket = new ReconnectingWebSocket(
    app_root + endpoint + "?channel=" + CHANNEL
  );  
  socket.debug = true;  

  return socket;
}

$(document).ready(function() {
  var player_id = getUrlParameter('participant_id');
      players.ego_id = player_id;

  // Append the canvas.
  $("#grid").append(pixels.canvas);

  // Opt out of the experiment.
  $("#opt-out").click(function() {
    allow_exit();
    window.location.href = "/questionnaire?participant_id=" + participant_id;
  });

  // Consent to the experiment.
  $("#go-to-experiment").click(function() {
    allow_exit();
    window.location.href = "/exp";
  });

  // Submit the questionnaire.
  $("#submit-questionnaire").click(function() {
    submitResponses();
  });

  $("#finish-reading").click(function() {
    $("#stimulus").hide();
    $("#response-form").show();
    $("#submit-response").removeClass("disabled");
    $("#submit-response").html("Submit");
  });

  $("#submit-response").click(function() {
    $("#submit-response").addClass("disabled");
    $("#submit-response").html("Sending...");

    var response = $("#reproduction").val();

    $("#reproduction").val("");

    reqwest({
      url: "/info/" + my_node_id,  // XXX my_node_id is undefined(?)
      method: "post",
      data: { contents: response, info_type: "Info" },
      success: function(resp) {
        console.log("Would call create_agent() if defined...");
      }
    });
  });

  if (settings.show_grid) {
    pixels.canvas.style.display = "inline";
  }

  if (settings.show_chatroom) {
    $("#chat").show();
  }

  $(pixels.canvas).contextmenu(function(e) {
    e.preventDefault();
    donateToClicked(-settings.donation);
  });

  $(pixels.canvas).click(function(e) {
    donateToClicked(settings.donation);
  });

  var donateToClicked = function(amt) {
    var row = pixels2cells(mouse[1]),
        column = pixels2cells(mouse[0]),
        recipient = players.nearest(row, column),
        donor = players.ego(),
        msg;

    if (recipient.id !== donor.id) {
      msg = {
        type: "donation_submitted", 
        recipient_id: recipient.id,
        donor_id: donor.id,
        amount: amt
      };
      sendToBackend(msg);
    }
  };

  var pixels2cells = function(pix) {
    return Math.floor(pix / (settings.block_size + settings.padding));
  };

  var onChatMessage = function (msg) {
    var name, 
        entry;

    if (settings.pseudonyms) {
      name = players.get(msg.player_id).name;
    } else {
      name = "Player " + msg.player_index;
    }
    entry = "<span class='name'>" + name + ":</span> " + msg.contents;
    $("#messages").append($("<li>").html(entry));
    $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
  };

  var onDonationProcessed = function (msg) {
    var ego = players.ego(),
        donor = players.get(msg.donor_id),
        recipient = players.get(msg.recipient_id),
        donor_name,
        recipient_name,
        entry;

    if (donor === ego) {
      donor_name = 'You';
    } else {
      donor_name = "Player " + donor.name;
    }

    if (recipient === ego) {
      recipient_name = 'you';
    } else {
      recipient_name = recipient.name;
    }    

    entry = donor_name + " gave " + recipient_name + " " + msg.amount;
    if (msg.amount === 1) {
      entry += " point.";
    } else {
      entry += " points.";
    }
    $("#messages").append($("<li>").html(entry));
    $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
  };

  var onGameStateChange = function (msg) {
    var ego,
        dollars,
        state;

    // Update remaining time.
    $("#time").html(Math.max(Math.round(msg.remaining_time), 0));

    // Update round.
    if (settings.num_rounds > 1) {
        $("#round").html(msg.round + 1);
    }

    // Update players.
    state = JSON.parse(msg.state_json);
    players.update(state.players);
    ego = players.ego();

    // Update food.
    food = [];
    for (var j = 0; j < state.food.length; j++) {
      food.push(
        new Food({
          id: state.food[j].id,
          position: state.food[j].position,
          color: state.food[j].color,
        })
      );
    }

    // Update walls if they haven't been created yet.
    if (walls.length === 0) {
      for (var k = 0; k < state.walls.length; k++) {
        walls.push(
          new Wall({
            position: state.walls[k].position,
            color: state.walls[k].color
          })
        );
      }
    }

    // Update displayed score.
    if (ego !== undefined) {
      $("#score").html(Math.round(ego.score));
      dollars = (ego.score * settings.dollars_per_point).toFixed(2);
      $("#dollars").html(dollars);
    }
  };

  function gameOver(msg) {
    $("#game-over").show();
    $("#dashboard").hide();
    $("#instructions").hide();
    $("#chat").hide();
    pixels.canvas.style.display = "none";
  }


  var inbox = openSocket('receive_chat');
  var outbox = openSocket('send_chat');

  outbox.onopen = function (event) {
    data = {
      type: 'connect',
      player_id: player_id,
    };
    sendToBackend(data);
  };

  inbox.onmessage = function (event) {
    if (event.data.indexOf(CHANNEL_MARKER) !== 0) { 
      console.log("Message was not on channel " + CHANNEL_MARKER + ". Ignoring.");
      return; 
    }
    var msg = JSON.parse(event.data.substring(CHANNEL_MARKER.length));
    switch(msg.type) {
      case "chat":
        onChatMessage(msg);
        break;
      case "donation_processed":
        onDonationProcessed(msg);
        break;
      case "state":
        onGameStateChange(msg);
        break;
      case "stop":
        gameOver(msg);
        break;
      default:
        console.log("Unrecognized message type " + msg.type + ' from backend.');
    }
  };

  function sendToBackend(data) {
    var msg = JSON.stringify(data);
    console.log("Sending message to the backend: " + msg);
    outbox.send(msg);
  }
  

  $("form").submit(function() {
    var msg = {
      type: 'chat',
      contents: $("#message").val(),
      player_id: players.ego().id,
      timestamp: Date.now() - start
    };
    sendToBackend(msg);
    $("#message").val("");
    return false;
  });

  //
  // Key bindings
  //
  var directions = ["up", "down", "left", "right"];
  var lock = false;
  directions.forEach(function(direction) {
    Mousetrap.bind(direction, function() {
      if (!lock) {
        players.ego().move(direction);
        var msg = {
          type: "move",
          player: players.ego().id,
          move: direction,
        };
        sendToBackend(msg);
      }
      lock = true;
      return false;
    });
    Mousetrap.bind(
      direction,
      function() {
        lock = false;
        return false;
      },
      "keyup"
    );
  });

  Mousetrap.bind("space", function () {
    var msg = {
      type: "plant_food", 
      player: players.ego().id,
      position: players.ego().position,
    };
    sendToBackend(msg);
  });

  function createBinding (key) {
    Mousetrap.bind(key[0].toLowerCase(), function () {
      players.ego().color = PLAYER_COLORS[key];
      var msg = {
        type: "change_color",
        player: players.ego().id, 
        color: PLAYER_COLORS[key]
      };
      sendToBackend(msg);
    });
  }

  if (settings.mutable_colors) {
    for (var key in PLAYER_COLORS) {
      if (PLAYER_COLORS.hasOwnProperty(key)) {
        createBinding(key);
      }
    }
  }
});

}(allow_exit, getUrlParameter, require, reqwest, settings, submitResponses));
