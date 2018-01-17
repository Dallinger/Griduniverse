/*global dallinger, require, settings */
/*jshint esversion: 6 */

(function (dallinger, require, settings) {

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

var CHANNEL = "griduniverse";
var CONTROL_CHANNEL = "griduniverse_ctrl";


var isSpectator = false;
var start = performance.now();
var food = [];
var foodConsumed = [];
var walls = [];
var row, column, rand;


var Player = function(settings) {
  if (!(this instanceof Player)) {
    return new Player();
  }
  this.id = settings.id;
  this.color = settings.color;
  this.score = settings.score;
  this.payoff = settings.payoff;
  this.name = settings.name;
  this.identity_visible = settings.identity_visible;
  return this;
};

var playerSet = (function () {

    var PlayerSet = function (settings) {
        if (!(this instanceof PlayerSet)) {
            return new PlayerSet(settings);
        }

        this._players = {};
        this.ego_id = settings.ego_id;
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

    PlayerSet.prototype.ego = function () {
      return this.get(this.ego_id);
    };

    PlayerSet.prototype.get = function (id) {
      return this._players[id];
    };

    PlayerSet.prototype.update = function(playerData) {
      var currentPlayerData, i;
      for (i = 0; i < playerData.length; i++) {
        currentPlayerData = playerData[i];
        this._players[currentPlayerData.id] = new Player(currentPlayerData);
      }
    };

    PlayerSet.prototype.group_scores = function () {
      var group_scores = {};

      this.each(function (i, player) {
        var color_name = player.color;
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

function chatName(player_id) {
  var ego = players.ego(),
    name,
    entry;
  if (id === ego) {
    name = "You";
  } else if (settings.pseudonyms) {
    name = players.get(player_id).name;
  } else if (player_id % 1 === 0) {
    name = "Player " + player_id;
  } else {
    // Non-integer player_id
    return '<span class="name">' + player_id + '</span>';
  }

  var salt = $("#grid").data("identicon-salt");
  var id = parseInt(player_id)-1;
    var entry = "<span class='name'>";
    entry = entry + " " + name + "</span> ";
    return entry;
}

  function onChatMessage(msg) {
    var entry = chatName(msg.player_id);
    $("#messages").append(($("<li>").text(": " + msg.contents)).prepend(entry));
    $("#chatlog").scrollTop($("#chatlog")[0].scrollHeight);
  }


  function onDonationProcessed(msg) {
    var donor = players.get(msg.donor_id),
      recipient_id = msg.recipient_id,
      team_idx,
      donor_name,
      recipient_name,
      donated_points,
      received_points,
      entry;

    donor_name = chatName(msg.donor_id);

    if (recipient_id === 'all') {
      recipient_name = '<span class="name">All players</span>';
    } else if (recipient_id.indexOf('group:') === 0) {
      team_idx = +recipient_id.substring(6);
        recipient_name = 'Everyone in <span class="name">' + settings.player_color_names[team_idx] + '</span>';
    } else {
        recipient_name = chatName(recipient_id);
    }

    if (msg.amount === 1) {
        donated_points = msg.amount + ' point.';
    } else {
        donated_points = msg.amount + ' points.';
    }

    if (msg.received === 1) {
      received_points = msg.received + ' point.';
    } else {
      received_points = msg.received + ' points.';
    }

    entry = donor_name + " contributed " + donated_points + " " + recipient_name + " received " + received_points;

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
      pushMessage("<span class='name'>Moderator:</span> Starting a donation round. Players cannot move, only donate.");
    } else {
      pushMessage("<span class='name'>Moderator:</span> Starting a consumption round. Players have to consume as much food as possible.");
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
  ego = players.ego();
  state = JSON.parse(msg.grid);
  players.update(state.players);
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
      var player_name = chatName(player.id);
      pushMessage('<span class="PlayerScore">' + Math.round(player.score) + '</span><span class="PlayerName">' + player_name + '</span>');
    }
  }
  if (settings.leaderboard_time) {
    settings.paused_game = true;
    setTimeout(function () {
        settings.paused_game = false;
        if (callback) callback();
      }, 1000 * settings.leaderboard_time);
  } else if (callback) callback();
}

  function gameOverHandler(player_id) {
  var callback;
  if (!isSpectator) {
    callback = function () {
      $("#dashboard").hide();
      $("#instructions").hide();
      $("#chat").hide();
      if (player_id) window.location.href = "/questionnaire?participant_id=" + player_id;
    };
  }
  return function (msg) {
    $("#game-over").show();
    return displayLeaderboards(msg, callback);
  };
}

$(document).ready(function() {
    var player_id = dallinger.getUrlParameter('participant_id');
    isSpectator = typeof player_id === 'undefined';
  var socketSettings = {
        'endpoint': 'chat',
        'broadcast': CHANNEL,
        'control': CONTROL_CHANNEL,
        'lagTolerance': 0.001,
        'callbackMap': {
          'chat': onChatMessage,
          'state': onGameStateChange,
          'new_round': displayLeaderboards,
        'stop': gameOverHandler(player_id)
        }
    };
    var socket = new GUSocket(socketSettings);

  socket.open().done(function () {
      var data = {
        type: 'connect',
        player_id: isSpectator ? 'spectator' : player_id
      };
      socket.send(data);
    });

  players.ego_id = player_id;
  console.log("ego id:");
  console.log(players.ego_id);
  $('#donate label').data('orig-text', $('#donate label').text());

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
      dallinger.submitResponses();
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

      dallinger.createInfo(my_node_id, {
        contents: response,
        info_type: 'Info'
    });
  });

  if (settings.show_chatroom) {
    $("#chat form").show();
  }

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
        msg;

    msg = {
      type: "donation_submitted",
      recipient_id: recipientId,
      donor_id: donor.id,
      amount: amt
    };
    socket.send(msg);
  };

  $("form").submit(function() {
    var chatmessage = $("#message").val().trim(),
        msg;

    if (! chatmessage) {
      return false;
    }

    console.log(players);
    console.log(players.ego());

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
    } catch(err) {
      console.error(err);
    } finally {
      $("#message").val("");
      return false;
    }
  });

  if (!isSpectator) {
    // Main game keys:
    // Donation click events:
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

}(dallinger, require, window.settings));
