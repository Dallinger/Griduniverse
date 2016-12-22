var util = require('util');
var css = require('dom-css');
var grid = require('./index');
var parse = require('parse-color');
var position = require('mouse-position');
var mousetrap = require('mousetrap');

BLUE = [0.50, 0.86, 1.00];
YELLOW = [1.00, 0.86, 0.50];

var rows = 40;
var columns = 40;

var data = [];
var background = [];
for (var i = 0; i < rows; i++) {
  for (var j = 0; j < columns; j++) {
    data.push([0, 0, 0]);
    background.push([0, 0, 0]);
  }
}

var pixels = grid(data, {
  root: document.body,
  rows: rows,
  columns: columns,
  size: 15,
  padding: 1,
  background: [0.1, 0.1, 0.1],
  formatted: true
});

Food = function (settings) {
    if (!(this instanceof Food)) {
        return new Food();
    }
    this.id = settings.id;
    this.position = settings.position;
    this.consumable = false;
    this.color = settings.color;
    return this;
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
                if (this.position[0] < rows - 1) {
                    this.position[0] += 1;
                }
                break;

            case "left":
                if (this.position[1] > 0) {
                    this.position[1] -= 1;
                }
                break;

            case "right":
                if (this.position[1] < columns - 1) {
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
        consumable: true,
        color: [1.00, 1.00, 1.00],
    })
];

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
        position: [5, columns - 5],
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
      background[i][2] * 0.95 + rand
    ];
  }

  data = background;

  // Update the food.
  for (i = 0; i < food.length; i++) {

      // Draw the food.
      idx = (food[i].position[0]) * columns + food[i].position[1];
      data[idx] = food[i].color;

      // Players digest the food.
      for (var j = 0; j < players.length; j++) {
        if (arraysEqual(players[j].position, food[i].position)) {
            food.splice(i, 1);
            players[j].score += 1;
            break;
        }
      }
  }

  // Update the players.
  players.forEach(function (p) {
      if (p.motion.auto) {
          p.move(p.motion.direction);
      }
      data[(p.position[0]) * columns + p.position[1]] = p.color;
  });

  pixels.update(data);

  document.getElementById("score").innerHTML = players[0].score;
});

//
// Key bindings
//
directions = ["up", "down", "left", "right"];
directions.forEach(function (direction){
    Mousetrap.bind(direction, function () {
        players[0].move(direction);
        return false;
    });
});

Mousetrap.bind("b", function () {
    players[0].color = BLUE;
});

Mousetrap.bind("y", function () {
    players[0].color = YELLOW;
});

start = Date.now();

function arraysEqual(arr1, arr2) {
    for(var i = arr1.length; i--;) {
        if(arr1[i] !== arr2[i])
            return false;
    }
    return true;
}
