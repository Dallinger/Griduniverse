/*global dallinger, store */
/*jshint esversion: 6 */

(function (dallinger, require, settings) {
  var grid = require("./index");
  var position = require("mouse-position");
  var Mousetrap = require("mousetrap");
  var $ = require("jquery");
  var gaussian = require("gaussian");
  var Color = require("color");
  var Identicon = require("./util/identicon");
  var _ = require("lodash");
  var md5 = require("./util/md5");
  var itemlib = require("./items");
  var socketlib = require("./gusocket");

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
      color[2] * 0.95 + rand,
    ];
  }

  function positionsAreEqual(a, b) {
    // Items with null positions are never co-located
    if (a === null || b === null) {
      return false;
    }
    return a[0] === b[0] && a[1] === b[1];
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
          if (!_.isNil(texture)) {
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
          this.data[idx] = Reflect.apply(func, this, [
            this.left + i,
            this.top + j,
            this.data[idx],
          ]);
        }
      }
    }
  }

  var background = [],
    color;
  for (var j = 0; j < settings.rows; j++) {
    for (var i = 0; i < settings.columns; i++) {
      color = [0, 0, 0];
      for (var k = 0; k < 15; k++) {
        color = animateColor(color);
      }
      background.push(color);
    }
  }

  var initialSection = new Section(background, 0, 0);

  var INVISIBLE_COLOR = [0.66, 0.66, 0.66];
  var CHANNEL = "griduniverse";
  var CONTROL_CHANNEL = "griduniverse_ctrl";

  var pixels = grid(initialSection.data, initialSection.textures, {
    rows: settings.window_rows,
    columns: settings.window_columns,
    size: settings.block_size,
    padding: settings.padding,
    background: [0.1, 0.1, 0.1],
    item_config: settings.item_config,
    sprites_url: settings.sprites_url,
    formatted: true,
  });

  var mouse = position(pixels.canvas);

  var isSpectator = false;
  var start = performance.now();
  var gridItems = new itemlib.GridItems();
  var walls = [];
  var wall_map = {};
  var transitionsUsed = new Set();
  var rand;

  var name2idx = function (name) {
    var names = settings.player_color_names;
    for (var idx = 0; idx < names.length; idx++) {
      if (names[idx] === name) {
        return idx;
      }
    }
  };

  var color2idx = function (color) {
    var colors = settings.player_colors;
    var value = color.join(",");
    for (var idx = 0; idx < colors.length; idx++) {
      if (colors[idx].join(",") === value) {
        return idx;
      }
    }
  };

  var color2name = function (color) {
    var idx = color2idx(color);
    return settings.player_color_names[idx];
  };

  var Wall = function (settings) {
    if (!(this instanceof Wall)) {
      return new Wall();
    }
    this.position = settings.position;
    this.color = settings.color;
    return this;
  };

  class Player {
    constructor(settings, dimness) {
      this.id = settings.id;
      this.position = settings.position;
      this.positionInSync = true;
      this.color = settings.color;
      this.motion_auto = settings.motion_auto;
      this.motion_direction = settings.motion_direction;
      this.motion_speed_limit = settings.motion_speed_limit;
      this.motion_timestamp = settings.motion_timestamp;
      this.score = settings.score;
      this.payoff = settings.payoff;
      this.name = settings.name;
      this.identity_visible = settings.identity_visible;
      this.dimness = dimness;
      this.replaceCurrentItem(settings.current_item || null);
    }

    move(direction) {
      function _isCrossable(position) {
        const hasWall = !_.isUndefined(wall_map[[position[1], position[0]]]);
        if (hasWall) {
          return false;
        }
        const itemHere = gridItems.atPosition(position);
        return _.isNull(itemHere) || itemHere.crossable;
      }
      const ts = performance.now() - start;
      const waitTime = 1000 / this.motion_speed_limit;

      this.motion_direction = direction;

      if (ts > this.motion_timestamp + waitTime) {
        const newPosition = this.position.slice();

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
          _isCrossable(newPosition) &&
          (!players.isPlayerAt(newPosition) || settings.player_overlap)
        ) {
          this.position = newPosition;
          this.motion_timestamp = ts;
          return true;
        }
      }
      return false;
    }

    replaceCurrentItem(item) {
      if (item && !(item instanceof itemlib.Item)) {
        item = new itemlib.Item(
          item.id,
          item.item_id,
          item.maturity,
          item.remaining_uses,
        );
      }

      this.currentItem = item;
    }

    getTransition() {
      const playerItem = this.currentItem;
      const position = this.position;
      const itemAtPos = gridItems.atPosition(position);
      let transitionId =
        ((playerItem && playerItem.itemId) || "") +
        "|" +
        ((itemAtPos && itemAtPos.itemId) || "");
      const lastTransitionId = "last_" + transitionId;
      let transition = settings.transition_config[lastTransitionId];

      if (itemAtPos && itemAtPos.remaining_uses === 1 && transition) {
        transitionId = lastTransitionId;
      } else {
        transition = settings.transition_config[transitionId];
      }

      if (!transition) {
        return null;
      }
      return { id: transitionId, transition: transition };
    }
  }

  class PlayerSet {
    constructor(settings) {
      this._players = new Map();
      this.ego_id = settings.ego_id;
      this.settings = settings;
    }

    isPlayerAt(position) {
      return Array.from(this._players.values()).some((player) =>
        positionsAreEqual(position, player.position),
      );
    }

    drawToGrid(grid) {
      let minScore, maxScore, d, color, player_color;

      if (settings.score_visible) {
        minScore = this.minScore();
        maxScore = this.maxScore();
      }

      for (const [id, player] of this._players) {
        /* It's unlikely that auto motion will keep identical pace to server-side auto-motion */
        /* this should be implemented either all on server or all on client */
        if (player.motion_auto) {
          player.move(player.motion_direction);
        }
        if (id === this.ego_id || settings.others_visible) {
          player_color = settings.player_colors[name2idx(player.color)];
          if (player.identity_visible) {
            color = player_color;
          } else {
            color =
              id === this.ego_id
                ? Color.rgb(player_color).desaturate(0.6).rgb().array()
                : INVISIBLE_COLOR;
          }
          if (settings.score_visible) {
            if (maxScore - minScore > 0) {
              d =
                0.75 * (1 - (player.score - minScore) / (maxScore - minScore));
            } else {
              d = 0.375;
            }
            color = Color.rgb(player_color).desaturate(d).rgb().array();
          } else {
            color = player_color;
          }
          var texture = 0;
          if (settings.use_identicons) {
            texture = parseInt(id, 10);
          }
          grid.plot(player.position[1], player.position[0], color, texture);
          if (id === this.ego_id) {
            store.set("color", color2name(color));
          }
        }
      }
    }

    nearest(row, column) {
      return Array.from(this._players.values()).reduce((nearest, player) => {
        const distance =
          Math.abs(row - player.position[0]) +
          Math.abs(column - player.position[1]);
        return nearest === null || distance < nearest.distance
          ? { player: player, distance: distance }
          : nearest;
      }, null).player;
    }

    getAdjacentPlayers() {
      /* Return a list of players adjacent to the ego player */
      const adjacentPlayers = [];
      const egoPostiion = this.ego().position;
      for (const [id, player] of this._players) {
        if (id === ego) {
          continue;
        }
        let position = player.position;
        let distanceX = Math.abs(position[0] - egoPostiion[0]);
        let distanceY = Math.abs(position[1] - egoPostiion[1]);
        if (distanceX <= 1 && distanceY <= 1) {
          adjacentPlayers.push(player);
        }
      }
      return adjacentPlayers;
    }

    ego() {
      return this.get(this.ego_id);
    }

    get(id) {
      return this._players.get(id);
    }

    count() {
      return this._players.size;
    }

    update(allPlayersData) {
      let freshPlayerData, existingPlayer, i;

      for (i = 0; i < allPlayersData.length; i++) {
        freshPlayerData = allPlayersData[i];
        existingPlayer = this._players.get(freshPlayerData.id);
        if (existingPlayer && existingPlayer.id === this.ego_id) {
          /* Don't override current player motion timestamp */
          freshPlayerData.motion_timestamp = existingPlayer.motion_timestamp;

          // Only override position from server if tremble is enabled,
          // or if we know the Player's position is out of sync with the server.
          // Otherwise, the ego player's motion is constantly jittery.
          if (
            settings.motion_tremble_rate === 0 &&
            existingPlayer.positionInSync
          ) {
            freshPlayerData.position = existingPlayer.position;
          } else {
            console.log("Overriding position from server!");
          }
        }
        let last_dimness = 1;
        if (!_.isUndefined(this._players.get(freshPlayerData.id))) {
          last_dimness = this._players.get(freshPlayerData.id).dimness;
        }
        this._players.set(
          freshPlayerData.id,
          new Player(freshPlayerData, last_dimness),
        );
      }
    }

    startScheduledAutosyncOfEgoPosition() {
      var self = this;
      setInterval(function () {
        var ego = self.ego();
        if (ego) {
          ego.positionInSync = false;
          console.log(
            `Scheduled marking of (${ego.id}) as out of sync with server.`,
          );
        }
      }, 5000);
    }

    maxScore() {
      return Array.from(this._players.values()).reduce(
        (max, player) => (player.score > max ? player.score : max),
        0,
      );
    }

    minScore() {
      return Array.from(this._players.values()).reduce(
        (min, player) => (player.score < min ? player.score : min),
        Infinity,
      );
    }

    each(callback) {
      let i = 0;
      for (const player of this._players.values()) {
        callback(i, player);
        i++;
      }
    }

    groupScores() {
      const scores = {};

      for (const player of this._players.values()) {
        let colorName = player.color;
        let cur_score = scores[colorName] || 0;
        scores[colorName] = cur_score + Math.round(player.score);
      }

      const groupOrder = Object.keys(scores).sort(function (a, b) {
        return scores[a] > scores[b] ? -1 : scores[a] < scores[b] ? 1 : 0;
      });

      return groupOrder.map((colorName) => ({
        name: colorName,
        score: groupScores[colorName],
      }));
    }

    playerScores() {
      return Array.from(this._players, ([id, player]) => ({
        id: id,
        name: player.name,
        score: player.score,
      })).sort((a, b) => b.score - a.score);
    }
  }

  // ego will be updated on page load
  var players = new PlayerSet({ ego_id: undefined });

  pixels.canvas.style.marginLeft = (window.innerWidth * 0.03) / 2 + "px";
  pixels.canvas.style.marginTop = (window.innerHeight * 0.04) / 2 + "px";
  document.body.style.transition = "0.3s all";
  document.body.style.background = "#ffffff";

  var startTime = performance.now();

  pixels.frame(function () {
    // Update the background.
    var ego = players.ego(),
      w = getWindowPosition(),
      section = new Section(background, w.left, w.top),
      dimness,
      rescaling,
      x,
      y;

    // Animate background for each visible cell
    section.map(function (x, y, color) {
      var newColor = animateColor(color);
      background[coordsToIdx(x, y, settings.columns)] = newColor;
      return newColor;
    });

    for (const [position, item] of gridItems.entries()) {
      if (players.isPlayerAt(position)) {
        if (!item.interactive && item.calories) {
          // Non-interactive items get consumed immediately
          // IF they have non-zero caloric value.
          gridItems.remove(position);
        }
      } else {
        var texture = undefined;
        if (item.item_id in pixels.itemTextures) {
          texture = item.item_id;
        }
        section.plot(position[1], position[0], item.color, texture);
      }
    }

    // Draw the players:
    players.drawToGrid(section);

    // Update ego player's view of their inventory, available
    // transitions, and info about the item they're co-occupying
    // a square with, if any:
    if (!_.isUndefined(ego)) {
      updateItemAtMyLocationDisplay(ego, gridItems);
      updateAvailableTransitionsDisplay(ego);
      updateMyInventoryDisplay(ego);
    }

    // Add the Gaussian mask.
    var elapsedTime = performance.now() - startTime;
    var visibilityNow = clamp(
      (settings.visibility * elapsedTime) /
        (1000 * settings.visibility_ramp_time),
      3,
      settings.visibility,
    );
    if (settings.highlightEgo) {
      visibilityNow = Math.min(visibilityNow, 4);
    }
    var g = gaussian(0, Math.pow(visibilityNow, 2));
    rescaling = 1 / g.pdf(0);

    if (!_.isUndefined(ego)) {
      x = ego.position[1];
      y = ego.position[0];
    } else {
      x = 1e100;
      y = 1e100;
    }
    section.map(function (i, j, color) {
      var newColor;
      // Draw walls
      if (settings.walls_visible) {
        color = wall_map[[i, j]] || color;
      }
      // Add Blur
      players.each(function (i, player) {
        dimness =
          g.pdf(distance(y, x, player.position[0], player.position[1])) *
          rescaling;
        player["dimness"] = dimness;
      });
      newColor = color;
      if (!isSpectator) {
        dimness = g.pdf(distance(x, y, i, j)) * rescaling;
        newColor = [color[0] * dimness, color[1] * dimness, color[2] * dimness];
      }
      return newColor;
    });
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

  function getWindowPosition() {
    var ego = players.ego(),
      w = {
        left: 0,
        top: 0,
        columns: settings.window_columns,
        rows: settings.window_rows,
      };

    if (!_.isUndefined(ego)) {
      w.left = clamp(
        ego.position[1] - Math.floor(settings.window_columns / 2),
        0,
        settings.columns - settings.window_columns,
      );
      w.top = clamp(
        ego.position[0] - Math.floor(settings.window_rows / 2),
        0,
        settings.rows - settings.window_rows,
      );
    }
    return w;
  }

  function bindGameKeys(socket) {
    var directions = ["up", "down", "left", "right"],
      repeatDelayMS = 1000 / settings.motion_speed_limit,
      lastDirection = null,
      repeatIntervalId = null;

    function moveInDir(direction) {
      var ego = players.ego();
      if (ego.move(direction)) {
        var msg = {
          type: "move",
          player_id: ego.id,
          move: direction,
          timestamp: ego.motion_timestamp,
        };
        socket.send(msg);
      }
    }

    function isChatting() {
      return $("#message").is(":focus");
    }

    directions.forEach(function (direction) {
      Mousetrap.bind(
        direction,
        function (e) {
          if (isChatting()) {
            return;
          }
          e.preventDefault();
          if (direction === lastDirection) {
            return;
          }

          // New direction may be pressed before previous dir key is released
          if (repeatIntervalId) {
            clearInterval(repeatIntervalId);
          }

          moveInDir(direction); // Move once immediately so there's no lag
          lastDirection = direction;
          repeatIntervalId = setInterval(moveInDir, repeatDelayMS, direction);
        },
        "keydown",
      );

      Mousetrap.bind(
        direction,
        function (e) {
          if (isChatting()) {
            return;
          }
          e.preventDefault();
          if (direction) {
            clearInterval(repeatIntervalId);
            lastDirection = null;
          }
        },
        "keyup",
      );
    });

    Mousetrap.bind("space", function (e) {
      if (isChatting()) {
        return;
      }
      e.preventDefault();
      var msg_type;
      var ego = players.ego();
      var position = ego.position;
      var item_at_pos = gridItems.atPosition(position);
      var player_item = ego.currentItem;
      var transition = ego.getTransition();
      if (!item_at_pos && !player_item) {
        // If there's nothing here, we try to plant food GU 1.0 style
        msg_type = "plant_food";
      } else if (transition) {
        // Check for a transition between objects. For now we don't do anything
        // client-side other checking that it exists. We could optimize display
        // updates later
        msg_type = "item_transition";
        transitionsUsed.add(transition.id);
      } else if (player_item && player_item.calories) {
        // If there's nothing here to transition with and we're holding something
        // edible, consume it.
        msg_type = "item_consume";
        player_item.remainingUses = player_item.remainingUses - 1;
        if (player_item.remainingUses < 1) {
          ego.replaceCurrentItem(null);
        }
      } else if (!player_item && item_at_pos && item_at_pos.portable) {
        // If there's a portable item here and we don't something in hand, pick it up.
        msg_type = "item_pick_up";
        gridItems.remove(position);
        ego.replaceCurrentItem(item_at_pos);
      }
      if (!msg_type) {
        return;
      }
      var msg = {
        type: msg_type,
        player_id: ego.id,
        position: position,
      };
      socket.send(msg);
    });

    Mousetrap.bind("d", function (e) {
      if (isChatting()) {
        return;
      }
      e.preventDefault();
      var ego = players.ego();
      var position = ego.position;
      var currentItem = ego.currentItem;
      if (!currentItem || gridItems.atPosition(position)) {
        return;
      }
      var msg = {
        type: "item_drop",
        player_id: ego.id,
        position: position,
      };
      socket.send(msg);
      ego.replaceCurrentItem(null);
      gridItems.add(currentItem, position);
    });

    if (settings.mutable_colors) {
      Mousetrap.bind("c", function () {
        var keys = settings.player_color_names,
          index = arraySearch(keys, players.ego().color),
          nextItem = keys[(index + 1) % keys.length],
          msg;

        players.ego().color = nextItem;
        msg = {
          type: "change_color",
          player_id: players.ego().id,
          color: players.ego().color,
        };
        socket.send(msg);
      });
    }

    if (settings.identity_signaling) {
      Mousetrap.bind("v", function () {
        var ego = players.ego(),
          msg;

        ego.identity_visible = !ego.identity_visible;
        msg = {
          type: "toggle_visible",
          player_id: ego.id,
          identity_visible: ego.identity_visible,
        };
        socket.send(msg);
      });
    }

    if (settings.build_walls) {
      Mousetrap.bind("w", function () {
        var msg = {
          type: "build_wall",
          player_id: players.ego().id,
          position: players.ego().position,
        };
        socket.send(msg);
      });
    }

    Mousetrap.bind("h", function () {
      settings.highlightEgo = !settings.highlightEgo;
    });
  }

  function chatName(player_id) {
    var ego = players.ego(),
      entry = "<span class='name'>",
      id = parseInt(player_id) - 1,
      salt = $("#grid").data("identicon-salt"),
      fg =
        settings.player_colors[name2idx(players.get(player_id).color)].concat(
          1,
        ),
      bg,
      identicon,
      name,
      options;

    if (id === ego) {
      name = "You";
    } else if (settings.pseudonyms) {
      name = players.get(player_id).name;
    } else if (player_id % 1 === 0) {
      name = "Player " + player_id;
    } else {
      // Non-integer player_id
      return '<span class="name">' + player_id + "</span>";
    }

    fg = fg.map(function (x) {
      return x * 255;
    });
    bg = fg.map(function (x) {
      return x * 0.66;
    });
    bg[3] = 255;
    options = {
      size: 10,
      foreground: fg,
      background: bg,
      format: "svg",
    };

    identicon = new Identicon(md5(salt + id), options).toString();
    if (settings.use_identicons) {
      entry =
        entry + " <img src='data:image/svg+xml;base64," + identicon + "' />";
    }
    entry = entry + " " + name + "</span> ";
    return entry;
  }

  function onChatMessage(msg) {
    var entry = chatName(msg.player_id);
    if (
      settings.spatial_chat &&
      players.get(msg.player_id).dimness < settings.chat_visibility_threshold
    ) {
      return;
    }
    $("#messages").append(
      $("<li>")
        .text(": " + msg.contents)
        .prepend(entry),
    );
    $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
  }

  function onColorChanged(msg) {
    store.set("color", msg.new_color);
    if (
      settings.spatial_chat &&
      players.get(msg.player_id).dimness < settings.chat_visibility_threshold
    ) {
      return;
    }
    pushMessage(
      "<span class='name'>Moderator:</span> " +
        chatName(msg.player_id) +
        " changed from team " +
        msg.old_color +
        " to team " +
        msg.new_color +
        ".",
    );
  }

  function onPlayerAdded(msg, socket) {
    var newPlayerId = msg.player_id,
      ego = players.ego();
    if (ego) {
      var playerId = ego.id;
    } else {
      playerId = dallinger.getUrlParameter("participant_id");
    }
    if (newPlayerId == playerId) {
      socket.addGameChannels(msg.broadcast_channel, msg.control_channel);
    }
  }

  function onMoveRejected(msg) {
    var offendingPlayerId = msg.player_id,
      ego = players.ego();

    if (ego && offendingPlayerId === ego.id) {
      ego.positionInSync = false;
      console.log(
        "Marking your player (" +
          ego.id +
          ") as out of sync with server. Should sync on next state update",
      );
    }
  }

  function onDonationProcessed(msg) {
    var recipient_id = msg.recipient_id,
      team_idx,
      donor_name,
      recipient_name,
      donated_points,
      received_points,
      entry;

    donor_name = chatName(msg.donor_id);

    if (recipient_id === "all") {
      recipient_name = '<span class="name">All players</span>';
    } else if (recipient_id.indexOf("group:") === 0) {
      team_idx = +recipient_id.substring(6);
      recipient_name =
        'Everyone in <span class="name">' +
        settings.player_color_names[team_idx] +
        "</span>";
    } else {
      recipient_name = chatName(recipient_id);
    }

    if (msg.amount === 1) {
      donated_points = msg.amount + " point.";
    } else {
      donated_points = msg.amount + " points.";
    }

    if (msg.received === 1) {
      received_points = msg.received + " point.";
    } else {
      received_points = msg.received + " points.";
    }

    entry =
      donor_name +
      " contributed " +
      donated_points +
      " " +
      recipient_name +
      " received " +
      received_points;

    $("#messages").append($("<li>").html(entry));
    $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
    $("#individual-donate, #group-donate").addClass("button-outline");
    $("#donate label").text($("#donate label").data("orig-text"));
    settings.donation_type = null;
  }

  function updateDonationStatus(donation_is_active) {
    // If alternating donation/consumption rounds, announce round type
    if (
      settings.alternate_consumption_donation &&
      settings.donation_active !== donation_is_active
    ) {
      if (donation_is_active) {
        pushMessage(
          "<span class='name'>Moderator:</span> Starting a donation round. Players cannot move, only donate.",
        );
      } else {
        pushMessage(
          "<span class='name'>Moderator:</span> Starting a consumption round. Players have to consume as much food as possible.",
        );
      }
    }
    // Update donation status
    settings.donation_active = donation_is_active;
  }

  function renderTransition(transition) {
    if (!transition) {
      return "";
    }
    const transitionVisibility = transition.transition.visible;
    const states = [
      transition.transition.actor_start,
      transition.transition.actor_end,
      transition.transition.target_start,
      transition.transition.target_end,
    ];

    const [aStartItem, aEndItem, tStartItem, tEndItem] = states.map(
      (state) => settings.item_config[state],
    );

    const aStartItemString = `✋${aStartItem ? aStartItem.name : "⬜"}`;
    const tStartItemString = tStartItem ? tStartItem.name : "⬜";
    if (transitionVisibility == "never") {
      return `${aStartItemString} + ${tStartItemString}`;
    }

    if (transitionVisibility == "seen" && !transitionsUsed.has(transition.id)) {
      var aEndItemString = "✋❓";
      var tEndItemString = "❓";
    } else {
      aEndItemString = `✋${aEndItem ? aEndItem.name : "⬜"}`;
      tEndItemString = tEndItem ? tEndItem.name : "⬜";
    }
    var actors_info = "";
    const required_actors = transition.transition.required_actors;
    // The total number of actors is the number of adjacent players plus one for ego (the current player)
    const neighboringActors = players.getAdjacentPlayers().length + 1;
    if (neighboringActors < required_actors) {
      actors_info = ` - not available: ${required_actors - neighboringActors} more players needed`;
    }
    return `${aStartItemString} + ${tStartItemString} → ${aEndItemString} + ${tEndItemString}${actors_info}`;
  }

  /**
   * If the current player is sharing a grid position with an interactive
   * item, we show information about it on the page.
   *
   * @param {Player} egoPlayer the current Player
   * @param {itemlib.GridItems} gridItems  the collection of all Items on the grid
   */
  function updateItemAtMyLocationDisplay(egoPlayer, gridItems) {
    const inspectedItem = gridItems.atPosition(egoPlayer.position);
    const $element = $("#location-contents-item");

    if (!inspectedItem) {
      $element.empty();
    } else {
      $element.html(inspectedItem.name);
    }
  }

  /**
   * Show transitions available for the item I'm currently carrying
   *
   * @param {Player} egoPlayer the current Player
   */
  function updateAvailableTransitionsDisplay(egoPlayer) {
    const transition = egoPlayer.getTransition();
    const $element = $("#transition-details");

    if (transition) {
      $element.html(renderTransition(transition));
    } else {
      // If we're holding an item with calories, indicate that we might
      // want to consume it.
      if (egoPlayer.currentItem && egoPlayer.currentItem.calories) {
        $element.html(`✋${egoPlayer.currentItem.name} + 😋`);
      } else {
        $element.empty();
      }
    }
  }

  /**
   * If the current player is carrying an Item, we show them what it is.
   *
   * @param {Player} egoPlayer the current Player
   */
  function updateMyInventoryDisplay(egoPlayer) {
    const item = egoPlayer.currentItem;
    const displayValue = item ? item.name : "";
    $("#inventory-item").text(displayValue);
  }

  function onGameStateChange(msg) {
    var $donationButtons = $(
        "#individual-donate, #group-donate, #public-donate, #ingroup-donate",
      ),
      $timeElement = $("#time"),
      $loading = $(".grid-loading"),
      cur_wall,
      ego,
      state,
      j,
      k;

    performance.mark("state_start");
    if ($loading.is(":visible")) $loading.fadeOut();

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

    // Update gridItems
    if (!_.isNil(state.items)) {
      gridItems = new itemlib.GridItems();
      for (j = 0; j < state.items.length; j++) {
        gridItems.add(
          new itemlib.Item(
            state.items[j].id,
            state.items[j].item_id,
            state.items[j].maturity,
            state.items[j].remaining_uses,
          ),
          state.items[j].position,
        );
      }
    }
    // Update walls if they haven't been created yet.
    if (!_.isUndefined(state.walls) && walls.length === 0) {
      for (k = 0; k < state.walls.length; k++) {
        cur_wall = state.walls[k];
        if (cur_wall instanceof Array) {
          cur_wall = {
            position: cur_wall,
            color: [0.5, 0.5, 0.5],
          };
        }
        walls.push(
          new Wall({
            position: cur_wall.position,
            color: cur_wall.color,
          }),
        );
        wall_map[[cur_wall.position[1], cur_wall.position[0]]] = cur_wall.color;
      }
    }

    // If new walls have been added, draw them
    if (!_.isUndefined(state.walls) && walls.length < state.walls.length) {
      for (k = walls.length; k < state.walls.length; k++) {
        cur_wall = state.walls[k];
        walls.push(
          new Wall({
            position: cur_wall.position,
            color: cur_wall.color,
          }),
        );
        wall_map[[cur_wall.position[1], cur_wall.position[0]]] = cur_wall.color;
      }
    }

    // Update displayed score, set donation info.
    if (!_.isUndefined(ego)) {
      $("#score").html(Math.round(ego.score));
      $("#dollars").html(ego.payoff.toFixed(2));
      window.state = msg.grid;
      window.ego = ego.id;
      if (
        settings.donation_active &&
        ego.score >= settings.donation_amount &&
        players.count() > 1
      ) {
        $donationButtons.prop("disabled", false);
      } else {
        $("#donation-instructions").text("");
        $donationButtons.prop("disabled", true);
      }
    }
  }

  function addWall(msg) {
    var wall = msg.wall;
    if (wall) {
      walls.push(
        new Wall({
          position: wall.position,
          color: wall.color,
        }),
      );
      wall_map[[wall.position[1], wall.position[0]]] = wall.color;
    }
  }

  function pushMessage(html) {
    $("#messages").append($("<li>").html(html));
    $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
  }

  function displayLeaderboards(msg, callback) {
    if (!settings.leaderboard_group && !settings.leaderboard_individual) {
      if (callback) {
        callback();
      }
      return;
    }
    var i;
    if (msg.type === "new_round") {
      pushMessage(
        "<span class='name'>Moderator:</span> the round " +
          msg.round +
          " standings are&hellip;",
      );
    } else {
      pushMessage(
        "<span class='name'>Moderator:</span> the final standings are &hellip;",
      );
    }
    if (settings.leaderboard_group) {
      if (settings.leaderboard_individual) {
        pushMessage("<em>Group</em>");
      }
      var groupScores = players.groupScores();
      var rgb_map = function (e) {
        return Math.round(e * 255);
      };
      for (i = 0; i < groupScores.length; i++) {
        var group = groupScores[i];
        var color = settings.player_colors[name2idx(group.name)].map(rgb_map);
        pushMessage(
          '<span class="GroupScore">' +
            group.score +
            '</span><span class="GroupIndicator" style="background-color:' +
            Color.rgb(color).string() +
            ';"></span>',
        );
      }
    }
    if (settings.leaderboard_individual) {
      if (settings.leaderboard_group) {
        pushMessage("<em>Individual</em>");
      }
      var playerScores = players.playerScores();
      for (i = 0; i < playerScores.length; i++) {
        var player = playerScores[i];
        var player_name = chatName(player.id);
        pushMessage(
          '<span class="PlayerScore">' +
            Math.round(player.score) +
            '</span><span class="PlayerName">' +
            player_name +
            "</span>",
        );
      }
    }
    if (settings.leaderboard_time) {
      settings.paused_game = true;
      setTimeout(function () {
        settings.paused_game = false;
        if (callback) {
          callback();
        }
      }, 1000 * settings.leaderboard_time);
    } else if (callback) {
      callback();
    }
  }

  function gameOverHandler(player_id) {
    var callback;
    if (!isSpectator) {
      callback = function () {
        $("#dashboard").hide();
        $("#instructions").hide();
        $("#chat").hide();
        if (player_id) {
          window.location.href = "/questionnaire?participant_id=" + player_id;
        }
      };
      pixels.canvas.style.display = "none";
    }
    return function (msg) {
      $("#game-over").show();
      return displayLeaderboards(msg, callback);
    };
  }

  $(function () {
    var player_id = dallinger.getUrlParameter("participant_id");
    isSpectator = _.isUndefined(player_id);
    var socketSettings = {
      endpoint: "chat",
      broadcast: CHANNEL,
      control: CONTROL_CHANNEL,
      lagTolerance: 0.001,
      callbackMap: {
        chat: onChatMessage,
        donation_processed: onDonationProcessed,
        color_changed: onColorChanged,
        state: onGameStateChange,
        new_round: displayLeaderboards,
        stop: gameOverHandler(player_id),
        wall_built: addWall,
        move_rejection: onMoveRejected,
        player_added: onPlayerAdded,
      },
    };
    const socket = new socketlib.GUSocket(socketSettings);

    socket.openExperiment().done(function () {
      var data = {
        type: "connect",
        player_id: isSpectator ? "spectator" : player_id,
      };
      socket.sendToExperiment(data);
    });

    players.ego_id = player_id;
    players.startScheduledAutosyncOfEgoPosition();
    $("#donate label").data("orig-text", $("#donate label").text());

    setInterval(function () {
      var delays = [],
        start_marks = performance.getEntriesByName("state_start", "mark");
      for (var i = 0; i < start_marks.length; i++) {
        if (start_marks.length > i + 2) {
          delays.push(start_marks[i + 1].startTime - start_marks[i].startTime);
        }
      }
      if (delays.length) {
        var average_delay =
          delays.reduce(function (sum, value) {
            return sum + value;
          }, 0) / delays.length;
        console.log(
          "Average delay between state updates: " + average_delay + "ms.",
        );
      }
    }, 5000);

    // Append the canvas.
    $("#grid").append(pixels.canvas);

    // Opt out of the experiment.
    $("#opt-out").on("click", function () {
      window.location.href = "/questionnaire?participant_id=" + player_id;
    });

    if (isSpectator) {
      $(".for-players").hide();
    }

    // Consent to the experiment.
    $("#go-to-experiment").on("click", function () {
      window.location.href = "/exp";
    });

    // Submit the questionnaire.
    $("#submit-questionnaire").on("click", function () {
      dallinger.submitResponses();
    });

    if (settings.show_grid) {
      pixels.canvas.style.display = "inline";
    }

    if (settings.show_chatroom) {
      $("#chat form").show();
    }

    var donateToClicked = function () {
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

      if (settings.donation_type === "individual") {
        recipient_id = recipient.id;
      } else if (settings.donation_type === "group") {
        recipient_id = "group:" + name2idx(recipient.color).toString();
      } else {
        return;
      }

      if (recipient_id !== donor.id) {
        msg = {
          type: "donation_submitted",
          recipient_id: recipient_id,
          donor_id: donor.id,
          amount: amt,
        };
        socket.send(msg);
      }
    };

    var donateToAll = function () {
      var donor = players.ego(),
        amt = settings.donation_amount,
        msg;

      msg = {
        type: "donation_submitted",
        recipient_id: "all",
        donor_id: donor.id,
        amount: amt,
      };
      socket.send(msg);
    };

    var donateToInGroup = function () {
      var donor = players.ego(),
        amt = settings.donation_amount,
        recipientId = "group:" + name2idx(donor.color).toString(),
        msg;

      msg = {
        type: "donation_submitted",
        recipient_id: recipientId,
        donor_id: donor.id,
        amount: amt,
      };
      socket.send(msg);
    };

    var pixels2cells = function (pix) {
      return Math.floor(pix / (settings.block_size + settings.padding));
    };

    $("form").on("submit", function () {
      var chatmessage = $("#message").val().trim(),
        msg;

      if (!chatmessage) {
        return false;
      }

      try {
        msg = {
          type: "chat",
          contents: chatmessage,
          player_id: players.ego().id,
          timestamp: performance.now() - start,
          broadcast: true,
        };
        // send directly to all clients
        socket.broadcast(msg);
        // Also send to the server for logging
        socket.send(msg);
      } catch (err) {
        console.error(err);
      } finally {
        $("#message").val("");
      }
      return false;
    });

    if (!isSpectator) {
      // Main game keys:
      bindGameKeys(socket);
      // Donation click events:
      $(pixels.canvas).on("click", function (e) {
        donateToClicked();
      });
      $("#public-donate").on("click", donateToAll);
      $("#ingroup-donate").on("click", donateToInGroup);
      $("#group-donate").on("click", function () {
        if (settings.donation_group) {
          $("#donate label").text("Click on a color");
          settings.donation_type = "group";
          $(this).prop("disabled", false);
          $(this).removeClass("button-outline");
          $("#individual-donate").addClass("button-outline");
        }
      });
      $("#individual-donate").on("click", function () {
        if (settings.donation_individual) {
          $("#donate label").text("Click on a player");
          settings.donation_type = "individual";
          $(this).removeClass("button-outline");
          $("#group-donate").addClass("button-outline");
        }
      });
    }
  });
})(dallinger, require, window.settings);
