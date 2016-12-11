var util = require('util');
var css = require('dom-css');
var grid = require('./index');
var parse = require('parse-color');
var position = require('mouse-position');
var mousetrap = require('mousetrap');

document.body.style.transition = '0.3s all';
document.body.style.background = '#ffffff';

var rows = 20;
var columns = 20;

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

Player = function (settings) {
    if (!(this instanceof Player)) return new Player();
    this.id = settings.id;
    this.position = settings.position;
    this.color = settings.color;
    this.motion = settings.motion;
    this.score = settings.score;
    return this;
};

Player.prototype.move = function (direction) {

    this.motion.direction = direction;

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
};

Player.prototype.direct = function (direction) {
    this.motion.direction = direction;
};

players = [
    new Player({
        id: 0,
        position: [0, 0],
        color: [0.50, 0.86, 1.00],
        motion: {
            auto: true,
            direction: "right",
            speed: 4,
            timestamp: 0,
        },
        score: 0,
    }),
    new Player({
        id: 1,
        position: [0, columns - 1],
        color: [1.00, 0.86, 0.50],
        motion: {
            auto: true,
            direction: "left",
            speed: 2,  // Blocks per second.
            timestamp: 0,
        },
        score: 0,
    }),
];

pixels.canvas.style.marginLeft = (window.innerWidth * 0.03) / 2 + 'px';
pixels.canvas.style.marginTop = (window.innerHeight * 0.04) / 2 + 'px';

var mouse = position(pixels.canvas);

var row, column, rand, color;
var hue = 0;

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

  // Update the players.
  data = background;
  ts = Date.now() - start;
  players.forEach(function (p) {
      if (p.motion.auto) {
        waitTime = 1000 / p.motion.speed;
        if(ts > p.motion.timestamp + waitTime) {
            p.move(p.motion.direction);
            p.motion.timestamp = ts;
        }
      }
      data[(p.position[0]) * columns + p.position[1]] = p.color;
  });
  pixels.update(data);
});

self = players[0];

//
// Key bindings
//
directions = ["up", "down", "left", "right"];
directions.forEach(function (direction){
    Mousetrap.bind(direction, function() {
        if (self.motion.auto) {
            self.direct(direction);
        } else {
            self.move(direction);
        }
    });
});

start = Date.now();
