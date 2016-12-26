var util = require('util');
var css = require('dom-css');
var grid = require('./index');
var parse = require('parse-color');
var position = require('mouse-position');
var mousetrap = require('mousetrap');
var colors = require('colors.css');
var io = require('socket.io-client')();
var $ = require("jquery");

// Parameters

BLUE = [0.50, 0.86, 1.00];
YELLOW = [1.00, 0.86, 0.50];
WHITE = [1.00, 1.00, 1.00];
GRID_BLOCK_SIZE = 15;
GRID_PADDING = 1;
RESPAWN_FOOD = true;
DOLLARS_PER_POINT = 0.02;
ROWS = 20;
COLUMNS = 20;

var data = [];
var background = [];
for (var i = 0; i < ROWS; i++) {
  for (var j = 0; j < COLUMNS; j++) {
    data.push([0, 0, 0]);
    background.push([0, 0, 0]);
  }
}

var pixels = grid(data, {
  root: document.body,
  rows: ROWS,
  columns: COLUMNS,
  size: GRID_BLOCK_SIZE,
  padding: GRID_PADDING,
  background: [0.1, 0.1, 0.1],
  formatted: true
});

Food = function (settings) {
    if (!(this instanceof Food)) {
        return new Food();
    }
    this.id = settings.id;
    this.position = settings.position;
    this.color = settings.color;
    return this;
};

respawnFood = function () {
    food.push(new Food({
        id: food.length + foodConsumed.length,
        position: [getRandomInt(0, COLUMNS), getRandomInt(0, ROWS)],
        color: WHITE,
    }));
};

Player = function (settings) {
    if (!(this instanceof Player)) {
        return new Player();
    }
    this.id = settings.id;
    this.position = settings.position;
    this.color = settings.color;
    this.motion = settings.motion;
    this.score = settings.score;
    return this;
};

Player.prototype.move = function (direction) {

    this.motion.direction = direction;

    ts = Date.now() - start;
    waitTime = 1000 / this.motion.speed;
    if (ts > this.motion._timestamp + waitTime) {

        switch (direction) {
            case "up":
                if (this.position[0] > 0) {
                    this.position[0] -= 1;
                }
                break;

            case "down":
                if (this.position[0] < ROWS - 1) {
                    this.position[0] += 1;
                }
                break;

            case "left":
                if (this.position[1] > 0) {
                    this.position[1] -= 1;
                }
                break;

            case "right":
                if (this.position[1] < COLUMNS - 1) {
                    this.position[1] += 1;
                }
                break;

            default:
                console.log("Direction not recognized.");
        }
        this.motion._timestamp = ts;
    }
};

food = [
    new Food({
        id: 0,
        position: [10, 10],
        color: WHITE,
    }),
    new Food({
        id: 1,
        position: [5, 5],
        color: WHITE,
    })
];

foodConsumed = [];

players = [
    new Player({
        id: 0,
        position: [0, 0],
        color: BLUE,
        motion: {
            auto: false,
            direction: "right",
            speed: 8,
            _timestamp: 0,
        },
        score: 0,
    }),
    new Player({
        id: 1,
        position: [5, COLUMNS - 5],
        color: YELLOW,
        motion: {
            auto: false,
            direction: "left",
            speed: 8,  // Blocks per second.
            _timestamp: 0,
        },
        score: 0,
    }),
];

pixels.canvas.style.marginLeft = (window.innerWidth * 0.03) / 2 + 'px';
pixels.canvas.style.marginTop = (window.innerHeight * 0.04) / 2 + 'px';
document.body.style.transition = '0.3s all';
document.body.style.background = '#ffffff';

var mouse = position(pixels.canvas);

var row, column, rand, color;

pixels.frame(function () {

  // Update the background.
  for (var i = 0; i < data.length; i++) {
      rand = Math.random() * 0.02;
      background[i] = [
          background[i][0] * 0.95 + rand,
          background[i][1] * 0.95 + rand,
          background[i][2] * 0.95 + rand,
    ];
  }

  data = background;

  // Update the food.
  for (i = 0; i < food.length; i++) {

      // Players digest the food.
      for (var j = 0; j < players.length; j++) {
        if (arraysEqual(players[j].position, food[i].position)) {
            foodConsumed.push(food.splice(i, 1));
            break;
        } else {
             // Draw the food.
            idx = (food[i].position[0]) * COLUMNS + food[i].position[1];
            data[idx] = food[i].color;
        }
      }
  }

  // Update the players' positions.
  players.forEach(function (p) {
      if (p.motion.auto) {
          p.move(p.motion.direction);
      }
      data[(p.position[0]) * COLUMNS + p.position[1]] = p.color;
  });

  pixels.update(data);
});

start = Date.now();

function arraysEqual(arr1, arr2) {
    for(var i = arr1.length; i--;) {
        if(arr1[i] !== arr2[i])
            return false;
    }
    return true;
}

function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

$(document).ready(function() {

    url = location.protocol + '//' + document.domain + ':' + location.port;
    var socket = io.connect(url);

    socket.on('state', function(msg) {

        // Update players.
        state = JSON.parse(msg.state_json);
        for (var i = 0; i < state.players.length; i++) {
            players[state.players[i].id].position = state.players[i].position;
            players[state.players[i].id].score = state.players[i].score;
        }

        // Update food.
        food = [];
        for (var j = 0; j < state.food.length; j++) {
            food.push(new Food({
                id: state.food[j].id,
                position: state.food[j].position,
                color: WHITE,
            }));
        }

        // Update displayed score.
        $("#score").html(players[EGO].score);
        dollars = (players[EGO].score * DOLLARS_PER_POINT).toFixed(2);
        $("#dollars").html(dollars);
    });

    socket.on('connect', function(msg) {
        console.log("connected!");
    });

    //
    // Key bindings
    //
    directions = ["up", "down", "left", "right"];
    lock = false;
    directions.forEach(function (direction){
        Mousetrap.bind(direction, function () {
            if (!lock) {
                players[0].move(direction);
                socket.emit('move', {
                    player: players[0].id,
                    move: direction,
                });
            }
            lock = true;
            return false;
        });
        Mousetrap.bind(direction, function () {
            lock = false;
            return false;
        }, "keyup");
    });

    Mousetrap.bind("b", function () {
        players[0].color = BLUE;
    });

    Mousetrap.bind("y", function () {
        players[0].color = YELLOW;
    });
});

// function serialize() {
//     return {
//         food,
//         players
//     }
// }
