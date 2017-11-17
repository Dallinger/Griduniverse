/*global create_agent, getUrlParameter, require, settings, submitResponses */
/*jshint esversion: 6 */

(function (getUrlParameter, require, reqwest, settings, submitResponses) {

var util = require("util");
var grid = require("./index");
var position = require("mouse-position");
var Mousetrap = require("mousetrap");
var ReconnectingWebSocket = require("reconnecting-websocket");
var $ = require("jquery");
var gaussian = require("gaussian");
var Color = require('color');
var Identicon = require('./util/identicon');
var md5 = require('./util/md5');

function coordsToIdx(x, y, columns) {
  return y * columns + x;
}

function animateColor(color) {
  if (settings.background_animation) {
    rand = Math.random() * 0.02;
  } else {
    rand = 0.01;
  }
  return [
    color[0] * 0.95 + rand,
    color[1] * 0.95 + rand,
    color[2] * 0.95 + rand
  ];
}

class Section {
  // Represents the currently visible section (window) of the grid

  constructor(data, left, top) {
    this.left = left;
    this.top = top;
    this.columns = settings.window_columns;
    this.rows = settings.window_rows;
    this.data = [];
    this.textures = [];
    // build data array for just this section
    for (var j = 0; j < this.rows; j++) {
      for (var i = 0; i < this.columns; i++) {
        this.data.push(data[this.sectionCoordsToGridIdx(i, j)]);
        this.textures.push(0);
      }
    }
  }

  gridCoordsToSectionIdx(x, y) {
    // Convert grid coordinates to section data array index
    return (y - this.top) * this.columns + (x - this.left);
  }

  sectionCoordsToGridIdx(x, y) {
    // Convert section coordinates to grid data array index
    return coordsToIdx(this.left + x, this.top + y, settings.columns);
  }

  plot(x, y, color, texture) {
    // Set color at position (x, y) in full-grid coordinates.
    if (x >= this.left && x < this.left + this.columns) {
      if (y >= this.top && y < this.top + this.rows) {
        this.data[this.gridCoordsToSectionIdx(x, y)] = color;
        if (texture !== undefined ){
          this.textures[this.gridCoordsToSectionIdx(x, y)] = texture;
        }
        background[coordsToIdx(x, y, settings.columns)] = color;
      }
    }
  }

  map(func) {
    // For each cell, call func with (x, y, color) to get the new color
    for (var j = 0; j < this.rows; j++) {
      for (var i = 0; i < this.columns; i++) {
        var idx = coordsToIdx(i, j, this.columns);
        this.data[idx] = Reflect.apply(
          func, this, [this.left + i, this.top + j, this.data[idx]]);
      }
    }
  }
}

var background = [];
for (var j = 0; j < settings.rows; j++) {
  for (var i = 0; i < settings.columns; i++) {
    var color = [0, 0, 0];
    for (var k = 0; k < 15; k++) {
      color = animateColor(color);
    }
    background.push(color);
  }
}
var initialSection = new Section(background, 0, 0);

var GREEN = [0.51, 0.69, 0.61];
var WHITE = [1.00, 1.00, 1.00];
var INVISIBLE_COLOR = [0.66, 0.66, 0.66];
var CHANNEL = "griduniverse";
var CONTROL_CHANNEL = "griduniverse_ctrl";

var pixels = grid(initialSection.data, initialSection.textures, {
  rows: settings.window_rows,
  columns: settings.window_columns,
  size: settings.block_size,
  padding: settings.padding,
  background: [0.1, 0.1, 0.1],
  formatted: true
});

var mouse = position(pixels.canvas);

var isSpectator = false;
var start = performance.now();
var food = [];
var foodConsumed = [];
var walls = [];
var row, column, rand, color;

name2idx = function(name) {
  var names = settings.player_color_names;
  for (var idx=0; idx < names.length; idx++) {
    if (names[idx] === name) {
      return idx;
    }
  }
};

color2idx = function(color) {
  var colors = settings.player_colors;
  var value = color.join(',');
  for (var idx=0; idx < colors.length; idx++) {
    if (colors[idx].join(',') === value) {
      return idx;
    }
  }
};

color2name = function(color) {
  var idx = color2idx(color);
  return settings.player_color_names[idx];
};

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
  this.payoff = settings.payoff;
  this.name = settings.name;
  this.identity_visible = settings.identity_visible;
  return this;
};

Player.prototype.move = function(direction) {

  function _hasWall(position) {
    for (var i = 0; i < walls.length; i++) {
      if (position == walls[i].position) {
         return false;
      }
    }
    return true;
  }

  this.motion_direction = direction;

  var ts = performance.now() - start,
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
    if (
      !_hasWall(newPosition) &
      (!players.isPlayerAt(position) || settings.player_overlap)
    ) {
      this.position = newPosition;
      this.motion_timestamp = ts;
    }
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
          id,
          minScore,
          maxScore,
          d,
          color;
      if (settings.score_visible) {
        minScore = this.minScore();
        maxScore = this.maxScore();
      }

      for (id in this._players) {
        if (this._players.hasOwnProperty(id)) {
          player = this._players[id];
          if (player.motion_auto) {
            player.move(player.motion_direction);
          }
          if (id === this.ego_id || settings.others_visible) {

            if (player.identity_visible) {
              color = player.color;
            } else {
              color = (id === this.ego_id) ? Color.rgb(player.color).desaturate(0.6).rgb().array() : INVISIBLE_COLOR;
            }
            if (settings.score_visible) {
              if (maxScore-minScore > 0) {
                d = 0.75 * (1 - (player.score-minScore)/(maxScore-minScore));
              } else {
                d = 0.375;
              }
              color = Color.rgb(player.color).desaturate(d).rgb().array();
            } else {
              color = player.color;
            }
            var texture = 0;
            if (settings.use_identicons) {
              texture = parseInt(id);
            }
            grid.plot(player.position[1], player.position[0], color, texture);
            if (id === this.ego_id) {
              store.set("color", color2name(color));
            }
          }
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

    PlayerSet.prototype.count = function () {
      return Object.keys(this._players).length;
    };

    PlayerSet.prototype.update = function (playerData) {
      var currentPlayerData,
          i;

      for (i = 0; i < playerData.length; i++) {
        currentPlayerData = playerData[i];
        this._players[currentPlayerData.id] = new Player(currentPlayerData);
      }
    };

    PlayerSet.prototype.maxScore = function () {
        var id;
        maxScore = 0;
        for (id in this._players) {
            if (this._players[id].score > maxScore) {
                maxScore = this._players[id].score;
            }
        }
        return maxScore;
    };

    PlayerSet.prototype.minScore = function () {
        var id;
        minScore = Infinity;
        for (id in this._players) {
            if (this._players[id].score < minScore) {
                minScore = this._players[id].score;
            }
        }
        return minScore;
    };

    PlayerSet.prototype.each = function (callback) {
      var i = 0;
      for (var id in this._players) {
        if (this._players.hasOwnProperty(id)) {
          callback(i, this._players[id]);
          i++;
        }
      }
    };

    PlayerSet.prototype.group_scores = function () {
      var group_scores = {};

      this.each(function (i, player) {
        var color_name = color2name(player.color);
        var cur_score = group_scores[color_name] || 0;
        group_scores[color_name] = cur_score + Math.round(player.score);
      });

      var group_order = Object.keys(group_scores).sort(function (a, b) {
        return group_scores[a] > group_scores[b] ? -1 : (group_scores[a] < group_scores[b] ? 1 : 0);
      });

      return group_order.map(function(color_name) {
        return {name: color_name, score: group_scores[color_name]};
      });
    };

    PlayerSet.prototype.player_scores = function () {
      var player_order = [];

      this.each(function(i, player) {
        player_order.push({id: player.id, name: player.name, score:player.score});
      });

      player_order = player_order.sort(function (a, b) {
        return a.score > b.score ? -1 : (a.score < b.score ? 1 : 0);
      });

      return player_order;
    };

    return PlayerSet;
}());

var GUSocket = (function () {

    var makeSocket = function (endpoint, channel, tolerance) {
      var ws_scheme = (window.location.protocol === "https:") ? 'wss://' : 'ws://',
          app_root = ws_scheme + location.host + '/',
          socket;

      socket = new ReconnectingWebSocket(
        app_root + endpoint + "?channel=" + channel + "&tolerance=" + tolerance
      );
      socket.debug = true;

      return socket;
    };

    var dispatch = function (self, event) {
        var marker = self.broadcastChannel + ':';
        if (event.data.indexOf(marker) !== 0) {
          console.log(
            "Message was not on channel " + self.broadcastChannel + ". Ignoring.");
          return;
        }
        var msg = JSON.parse(event.data.substring(marker.length));

        var callback = self.callbackMap[msg.type];
        if (typeof callback !== 'undefined') {
          callback(msg);
        } else {
          console.log("Unrecognized message type " + msg.type + ' from backend.');
        }
    };


    /*
     * Public API
     */
    var Socket = function (settings) {
        if (!(this instanceof Socket)) {
            return new Socket(settings);
        }

        var self = this,
            isOpen = $.Deferred(),
            tolerance = typeof(settings.lagTolerance) !== 'undefined' ? settings.lagTolerance : 0.1;

        this.broadcastChannel = settings.broadcast;
        this.controlChannel = settings.control;
        this.callbackMap = settings.callbackMap;


        this.socket = makeSocket(
          settings.endpoint, this.broadcastChannel, tolerance);

        this.socket.onmessage = function (event) {
          dispatch(self, event);
        };
    };

    Socket.prototype.open = function () {
      var isOpen = $.Deferred();

      this.socket.onopen = function (event) {
        isOpen.resolve();
      };

      return isOpen;
    };

    Socket.prototype.send = function (data) {
      var msg = JSON.stringify(data),
          channel = this.controlChannel;

      console.log("Sending message to the " + channel + " channel: " + msg);
      this.socket.send(channel + ':' + msg);
    };

    Socket.prototype.broadcast = function (data) {
      var msg = JSON.stringify(data),
          channel = this.broadcastChannel;

      console.log("Broadcasting message to the " + channel + " channel: " + msg);
      this.socket.send(channel + ':' + msg);
    };


    return Socket;
}());

// ego will be updated on page load
var players = playerSet({'ego_id': undefined});

pixels.canvas.style.marginLeft = window.innerWidth * 0.03 / 2 + "px";
pixels.canvas.style.marginTop = window.innerHeight * 0.04 / 2 + "px";
document.body.style.transition = "0.3s all";
document.body.style.background = "#ffffff";

var startTime = performance.now();

pixels.frame(function() {
  // Update the background.
  var ego = players.ego(),
      w = getWindowPosition(),
      limitVisibility,
      dimness,
      rescaling,
      i, j, x, y;

  var section = new Section(background, w.left, w.top);

  // Animate background for each visible cell
  section.map(function(x, y, color) {
    var newColor = animateColor(color);
    background[coordsToIdx(x, y, settings.columns)] = newColor;
    return newColor;
  });

  for (i = 0; i < food.length; i++) {
    // Players digest the food.
    if (players.isPlayerAt(food[i].position)) {
      foodConsumed.push(food.splice(i, 1));
    } else {
      if (settings.food_visible) {
        section.plot(food[i].position[1], food[i].position[0], food[i].color);
      }
    }
  }

  // Draw the players:
  players.drawToGrid(section);

  // Draw the walls.
  if (settings.walls_visible) {
    walls.forEach(function(w) {
      section.plot(w.position[1], w.position[0], w.color);
    });
  }

  // Add the Gaussian mask.
  var elapsedTime = performance.now() - startTime;
  var visibilityNow = clamp(
    (settings.visibility * elapsedTime) / (1000 * settings.visibility_ramp_time),
    3,
    settings.visibility
  );
  if (settings.highlightEgo) {
    visibilityNow = Math.min(visibilityNow, 4);
  }
  var g = gaussian(0, Math.pow(visibilityNow, 2));
  rescaling = 1 / g.pdf(0);

  if (!isSpectator) {
    if (typeof ego !== "undefined") {
      x = ego.position[1];
      y = ego.position[0];
    } else {
      x = 1e100;
      y = 1e100;
    }
    section.map(function(i, j, color) {
      dimness = g.pdf(distance(x, y, i, j)) * rescaling;
      var newColor = [
        color[0] * dimness,
        color[1] * dimness,
        color[2] * dimness
      ];
      return newColor;
    });
  }
  pixels.update(section.data, section.textures);
});

function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

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

function arraySearch(arr, val) {
    for (var i = 0; i < arr.length; i++) {
      if (arraysEqual(arr[i], val)) {
        return i;
      }
    }
    return false;
}

function getRandomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getWindowPosition() {
  var ego = players.ego(),
      w = {
        left: 0,
        top: 0,
        columns: settings.window_columns,
        rows: settings.window_rows
      };

  if (typeof ego !== 'undefined') {
    w.left = clamp(
      ego.position[1] - Math.floor(settings.window_columns / 2),
      0, settings.columns - settings.window_columns);
    w.top = clamp(
      ego.position[0] - Math.floor(settings.window_rows / 2),
      0, settings.rows - settings.window_rows);
  }
  return w;
}

function bindGameKeys(socket) {
  var directions = ["up", "down", "left", "right"],
      repeatDelayMS = 1000 / settings.motion_speed_limit,
      lastDirection = null,
      repeatIntervalId = null,
      highlightEgo = false;

  function moveInDir(direction) {
    players.ego().move(direction);
    var msg = {
      type: "move",
      player_id: players.ego().id,
      move: direction
    };
    socket.send(msg);
  }

  directions.forEach(function(direction) {
    Mousetrap.bind(
      direction,
      function() {
        if (direction === lastDirection) {
          return;
        }

        // New direction may be pressed before previous dir key is released
        if (repeatIntervalId) {
          console.log("Clearing interval for new keydown");
          clearInterval(repeatIntervalId);
        }

        moveInDir(direction); // Move once immediately so there's no lag
        lastDirection = direction;
        repeatIntervalId = setInterval(moveInDir, repeatDelayMS, direction);
        console.log("Repeating new direction: " + direction + " (" + repeatIntervalId + ")");
      },
      'keydown'
    );

    Mousetrap.bind(
      direction,
      function() {
        if (direction) {
          console.log("Calling clearInterval() for " + direction + " (" + repeatIntervalId + ")");
          clearInterval(repeatIntervalId);
          lastDirection = null;
        }
      },
      "keyup"
    );

  });

  Mousetrap.bind("space", function () {
    var msg = {
      type: "plant_food",
      player_id: players.ego().id,
      position: players.ego().position
    };
    socket.send(msg);
  });

  if (settings.mutable_colors) {
    Mousetrap.bind('c', function () {
      keys = settings.player_color_names;
      values = settings.player_colors;
      index = arraySearch(values, players.ego().color);
      nextItem = keys[(index + 1) % keys.length];
      players.ego().color = settings.player_colors[name2idx(nextItem)];
      var msg = {
        type: "change_color",
        player_id: players.ego().id,
        color: players.ego().color
      };
      socket.send(msg);
    });
  }

  if (settings.identity_signaling) {
    Mousetrap.bind("v", function () {
      var ego = players.ego();
      ego.identity_visible = !ego.identity_visible;
      var msg = {
        type: "toggle_visible",
        player_id: ego.id,
        identity_visible: ego.identity_visible
      };
      socket.send(msg);
    });
  }

  if (settings.build_walls) {
    Mousetrap.bind("w", function () {
      var msg = {
        type: "build_wall",
        player_id: players.ego().id,
        position: players.ego().position
      };
      socket.send(msg);
    });
  }

  Mousetrap.bind("h", function () {
      settings.highlightEgo = !settings.highlightEgo;
  });
}

function onChatMessage(msg) {
  var name,
      entry;

  if (settings.pseudonyms) {
    name = players.get(msg.player_id).name;
  } else {
    name = "Player " + msg.player_index;
  }
  var salt = $("#grid").data("identicon-salt");
  var id = parseInt(msg.player_id)-1;
  var fg = players.get(msg.player_id).color.concat(1);
  fg = fg.map(function(x) { return x * 255; });
  bg = fg.map(function(x) { return (x * 0.66); });
  bg[3] = 255;
  var options = {
    size: 10,
    foreground: fg,
    background: bg,
    format: 'svg'
  };
  var identicon = new Identicon(md5(salt + id), options).toString();
  var entry = "<span class='name'>" + name;
  if (settings.use_identicons) {
    entry = entry + " <img src='data:image/svg+xml;base64," + identicon + "' />";
  }
  entry = entry + ":</span> ";
  $("#messages").append(($("<li>").text(msg.contents)).prepend(entry));
  $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
}

  function onColorChanged(msg) {
    var name;
    store.set("color", msg.new_color);
    if (settings.pseudonyms) {
      name = players.get(msg.player_id).name;
    } else {
      name = "Player " + msg.player_index;
    }
    pushMessage("<span class='name'>Moderator:</span> " + name + ' changed from team ' + msg.old_color + ' to team ' + msg.new_color + '.');
  }

  function onDonationProcessed(msg) {
    var ego = players.ego(),
      donor = players.get(msg.donor_id),
      recipient_id = msg.recipient_id,
      team_idx,
      donor_name,
      recipient_name,
      entry;

    if (donor === ego) {
      donor_name = 'You';
    } else {
      donor_name = "Player " + donor.name;
    }

    if (ego && recipient_id === ego.id) {
    recipient_name = 'you';
  } else if (recipient_id === 'all') {
    recipient_name = 'all players';
  } else if (recipient_id.indexOf('group:') === 0) {
    team_idx = +recipient_id.substring(6);
    recipient_name = 'all ' + settings.player_color_names[team_idx] + ' players';
  } else {
    recipient_name = players.get(recipient_id).name;
  }

  entry = donor_name + " contributed " + msg.amount;
  if (msg.amount === 1) {
    entry += " point ";
  } else {
    entry += " points ";
  }
  entry += "to " + recipient_name + ", which is increased to 1.4 and split up."
  $("#messages").append($("<li>").html(entry));
  $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
  $('#individual-donate, #group-donate').addClass('button-outline');
  $('#donate label').text($('#donate label').data('orig-text'));
  settings.donation_type = null;
}

function updateDonationStatus(donation_is_active) {
  // If alternating donation/consumption rounds, announce round type
  if (settings.alternate_consumption_donation && (settings.donation_active !== donation_is_active)) {
    if (donation_is_active) {
      pushMessage("<span class='name'>Moderator:</span> Starting a contribution round: you cannot move, only contribute. Remember, anything you contribute is multiplied by 1.4 before it's split up.");
    } else {
      pushMessage("<span class='name'>Moderator:</span> Starting a collection round: collect as much food as possible.");
    }
  }
  // Update donation status
  settings.donation_active = donation_is_active;
}

function onGameStateChange(msg) {
  var $donationButtons = $('#individual-donate, #group-donate, #public-donate, #ingroup-donate'),
      $timeElement = $("#time"),
      ego,
      state;

  if (settings.paused_game) {
    $timeElement.html(0);
    return;
  }

  // Update remaining time.
  $timeElement.html(Math.max(Math.round(msg.remaining_time), 0));

  // Update round.
  if (settings.num_rounds > 1) {
      $("#round").html(msg.round + 1);
  }

  // Update players.
  state = JSON.parse(msg.grid);
  players.update(state.players);
  ego = players.ego();

  updateDonationStatus(state.donation_active);

  // Update food.
  food = [];
  for (var j = 0; j < state.food.length; j++) {
    food.push(
      new Food({
        id: state.food[j].id,
        position: state.food[j].position,
        color: state.food[j].color
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

  // If new walls have been added, draw them
  if (walls.length !== state.walls.length) {
    for (var k = walls.length; k < state.walls.length; k++) {
      walls.push(
        new Wall({
          position: state.walls[k].position,
          color: state.walls[k].color
        })
      );
    }
  }

  // Update displayed score, set donation info.
  if (ego !== undefined) {
    $("#score").html(Math.round(ego.score));
    $("#dollars").html(ego.payoff.toFixed(2));
    window.state = msg.grid;
    window.ego = ego.id;
    if (settings.donation_active &&
        ego.score >= settings.donation_amount &&
        players.count() > 1
    ) {
      $donationButtons.prop('disabled', false);
    } else {
      $('#donation-instructions').text('');
      $donationButtons.prop('disabled', true);
    }
  }
}

function pushMessage(html) {
  $("#messages").append(($("<li>").html(html)));
  $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
}

function displayLeaderboards(msg, callback) {
  if (!settings.leaderboard_group && !settings.leaderboard_individual) {
    if (callback) callback();
    return;
  }
  var i;
  if (msg.type == 'new_round') {
    pushMessage("<span class='name'>Moderator:</span> the round " + msg.round + ' standings are&hellip;');
  } else {
    pushMessage("<span class='name'>Moderator:</span> the final standings are &hellip;");
  }
  if (settings.leaderboard_group) {
    if (settings.leaderboard_individual) {
      pushMessage('<em>Group</em>');
    }
    var group_scores = players.group_scores();
    var rgb_map = function (e) { return Math.round(e * 255); };
    for (i = 0; i < group_scores.length; i++) {
      var group = group_scores[i];
      var color = settings.player_colors[name2idx(group.name)].map(rgb_map);
      pushMessage('<span class="GroupScore">' + group.score + '</span><span class="GroupIndicator" style="background-color:' + Color.rgb(color).string() +';"></span>');
    }
  }
  if (settings.leaderboard_individual) {
    if (settings.leaderboard_group) {
      pushMessage('<em>Individual</em>');
    }
    var player_scores = players.player_scores();
    var ego_id = players.ego_id;
    for (i = 0; i < player_scores.length; i++) {
      var player = player_scores[i];
      var player_name = player.name;
      if (ego_id == player.id) {
        player_name = '<em>' + player_name + ' (You)</em>';
      }
      pushMessage('<span class="PlayerScore">' + Math.round(player.score) + '</span><span class="PlayerName">' + player_name + '</span>');
    }
  }
  if (settings.intergroup_competition > 2) {
    pushMessage("<span class='name'>Moderator:</span> Remember, the group with the most points at the end of the game wins the whole pot.");
  }
  if (settings.intragroup_competition > 2) {
    pushMessage("<span class='name'>Moderator:</span> Remember, the player in each group with the highest point total will receive that whole group's earnings.");
  }
  if (settings.leaderboard_time) {
    settings.paused_game = true;
    setTimeout(function () {
        settings.paused_game = false;
        if (callback) callback();
      }, 1000 * settings.leaderboard_time);
  } else if (callback) callback();
}

function gameOverHandler(isSpectator, player_id) {
  var callback;
  if (!isSpectator) {
    callback = function () {
      $("#dashboard").hide();
      $("#instructions").hide();
      $("#chat").hide();
      if (player_id) window.location.href = "/questionnaire?participant_id=" + player_id;
    };
    pixels.canvas.style.display = "none";
  }
  return function (msg) {
    $("#game-over").show();
    return displayLeaderboards(msg, callback);
  };
}

$(document).ready(function() {
  var player_id = getUrlParameter('participant_id');
  isSpectator = typeof player_id === 'undefined';
  var socketSettings = {
        'endpoint': 'chat',
        'broadcast': CHANNEL,
        'control': CONTROL_CHANNEL,
        'lagTolerance': 0.001,
        'callbackMap': {
          'chat': onChatMessage,
          'donation_processed': onDonationProcessed,
          'change_color': onColorChanged,
          'state': onGameStateChange,
          'new_round': displayLeaderboards,
          'stop': gameOverHandler(isSpectator, player_id)
        }
      },
  socket = new GUSocket(socketSettings);

  socket.open().done(function () {
      var data = {
        type: 'connect',
        player_id: isSpectator ? 'spectator' : player_id
      };
      socket.send(data);
    }
  );

  players.ego_id = player_id;
  $('#donate label').data('orig-text', $('#donate label').text());

  // Append the canvas.
  $("#grid").append(pixels.canvas);

  // Opt out of the experiment.
  $("#opt-out").click(function() {
    window.location.href = "/questionnaire?participant_id=" + player_id;
  });

  if (isSpectator) {
    $(".for-players").hide();
  }

  // Consent to the experiment.
  $("#go-to-experiment").click(function() {
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
    $("#chat form").show();
  }

  var donateToClicked = function() {
    var w = getWindowPosition(),
        row = w.top + pixels2cells(mouse[1]),
        column = w.left + pixels2cells(mouse[0]),
        recipient = players.nearest(row, column),
        donor = players.ego(),
        amt = settings.donation_amount,
        recipient_id,
        msg;

    if (!settings.donation_active) {
      return;
    }

    if (amt > donor.score) {
      return;
    }

    if (settings.donation_type === 'individual') {
      recipient_id = recipient.id;
    } else if (settings.donation_type === 'group') {
      recipient_id = 'group:' +  color2idx(recipient.color).toString();
    } else {
      return;
    }

    if (recipient_id !== donor.id) {
      msg = {
        type: "donation_submitted",
        recipient_id: recipient_id,
        donor_id: donor.id,
        amount: amt
      };
      socket.send(msg);
    }
  };

  var donateToAll = function() {
    var donor = players.ego(),
        amt = settings.donation_amount,
        msg;

    msg = {
      type: "donation_submitted",
      recipient_id: 'all',
      donor_id: donor.id,
      amount: amt
    };
    socket.send(msg);
  };

  var donateToInGroup = function () {
    var donor = players.ego(),
        amt = settings.donation_amount,
        recipientId = 'group:' +  color2idx(donor.color).toString(),
        msg;

    msg = {
      type: "donation_submitted",
      recipient_id: recipientId,
      donor_id: donor.id,
      amount: amt
    };
    socket.send(msg);
  };

  var pixels2cells = function(pix) {
    return Math.floor(pix / (settings.block_size + settings.padding));
  };

  $("form").submit(function() {
    var chatmessage = $("#message").val().trim(),
        msg;

    if (! chatmessage) {
      return false;
    }

    try {
      msg = {
        type: 'chat',
        contents: chatmessage,
        player_id: players.ego().id,
        timestamp: performance.now() - start,
        broadcast: true
      };
      // send directly to all clients
      socket.broadcast(msg);
      // send to the server for recording
      socket.send(msg);
    } catch(err) {
      console.error(err);
    } finally {
      $("#message").val("");
      return false;
    }
  });


  if (!isSpectator) {
    // Main game keys:
    bindGameKeys(socket);
    // Donation click events:
    $(pixels.canvas).click(function (e) {
      donateToClicked();
    });
    $('#public-donate').click(donateToAll);
    $('#ingroup-donate').click(donateToInGroup);
    $('#group-donate').click(function () {
      if (settings.donation_group) {
        $('#donate label').text('Click on a color');
        settings.donation_type = 'group';
        $(this).prop('disabled', false);
        $(this).removeClass('button-outline');
        $('#individual-donate').addClass('button-outline');
      }
    });
    $('#individual-donate').click(function () {
      if (settings.donation_individual) {
        $('#donate label').text('Click on a player');
        settings.donation_type = 'individual';
        $(this).removeClass('button-outline');
        $('#group-donate').addClass('button-outline');
      }
    });
  }

});

}(getUrlParameter, require, reqwest, settings, submitResponses));
