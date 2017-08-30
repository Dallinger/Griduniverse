var parse = require("parse-color");
var isnumber = require("is-number");
var isstring = require("is-string");
var isarray = require("is-array");
var convert = require("./util/convert");
var layout = require("./util/layout");
var texcoord = require("./util/texcoord");
var range = require("./util/range");
var pixdenticon = require("./util/pixdenticon");
var md5 = require("./util/md5");

function Pixels(data, textures, opts) {
  if (!(this instanceof Pixels)) return new Pixels(data, textures, opts);
  var self = this;
  opts = opts || {};
  this.opts = opts;
  var num_identicons = 100;

  opts.background = opts.background || [ 0.5, 0.5, 0.5 ];
  opts.size = isnumber(opts.size) ? opts.size : 10;
  opts.padding = isnumber(opts.padding) ? opts.padding : 2;

  if (isstring(opts.background))
    opts.background = parse(opts.background).rgb.map(function(c) {
      return c / 255;
    });

  if (isarray(data[0]) && data[0].length !== 3) {
    opts.rows = data.length;
    opts.columns = data[0].length;
  }

  if (!opts.rows || !opts.columns) {
    opts.rows = opts.columns = Math.round(Math.sqrt(data.length));
  }

  var width = opts.columns * opts.size + (opts.columns + 1) * opts.padding;
  var height = opts.rows * opts.size + (opts.rows + 1) * opts.padding;

  var canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  if (opts.root) opts.root.appendChild(canvas);

  var colors = opts.formatted ? data : convert(data);
  var texcoords = texcoord(
    opts.rows,
    opts.columns,
    textures,
    num_identicons
  );

  var positions = layout(
    opts.rows,
    opts.columns,
    2 * opts.padding / width,
    2 * opts.size / width,
    width / height
  );

  var regl = require("regl")(canvas);

  var initial_texture = [];
  for (row = 0; row < opts.size; row++) {
    rowdata = []
    for (col = 0; col < opts.size; col++) {
      rowdata.push([255, 255, 255]);
    }
    initial_texture.push(rowdata);
  }
  var salt = $("#grid").data("identicon-salt");
  for (var i = 0; i < num_identicons; i++) {
    texture = new pixdenticon(md5(salt + i), opts.size).render().buffer;
    for (row = 0; row < opts.size; row++) {
      initial_texture.push(texture[row]);
    }
  }

  var texture = regl.texture(initial_texture);

  var squares = regl({
    vert: `
    precision mediump float;
    attribute vec2 position;
    attribute vec2 texcoords;
    attribute vec3 color;
    varying vec3 vcolor;
    varying vec2 v_texcoords;
    void main() {
      gl_PointSize = float(${opts.size});
      gl_Position = vec4(position.x, position.y, 0.0, 1.0);
      v_texcoords = texcoords;
      vcolor = color;
    }
    `,
    frag: `
    precision mediump float;
    varying vec3 vcolor;
    varying vec2 v_texcoords;
    uniform sampler2D vtexture;
    void main() {
      vec4 texture;
      texture = texture2D(vtexture, v_texcoords);
      gl_FragColor = texture * vec4(vcolor.r, vcolor.g, vcolor.b, 1.0);
    }
    `,
    attributes: { position: regl.prop("position"), texcoords: regl.prop("texcoords"), color: regl.prop("color")},
    primitive: "triangles",
    count: colors.length * 6,
    uniforms: { vtexture: texture }
  });

  var expanded_colors = [];
  for(var i = 0; i < colors.length; ++i){
    for(var n = 0; n < 6; ++n) {
      expanded_colors.push(colors[i]);
    }
  }

  var buffer = { position: regl.buffer(positions), texcoords: regl.buffer(texcoords), color: regl.buffer(expanded_colors)};

  var draw = function(positions, texcoords, colors) {
    regl.clear({ color: opts.background.concat([ 1 ]) });
    squares({ position: positions, texcoords: texcoords, color: colors });
  };

  draw(buffer.position, buffer.texcoords, buffer.color);

  self._buffer = buffer;
  self._draw = draw;
  self._formatted = opts.formatted;
  self.canvas = canvas;
  self.frame = regl.frame;
}

Pixels.prototype.update = function(data, textures) {
  var self = this;
  var colors = self._formatted ? data : convert(data);
  var expanded_colors = [];

  for(var i = 0; i < colors.length; ++i){
    for(var n = 0; n < 6; ++n) {
      expanded_colors.push(colors[i]);
    }
  }

  var opts = this.opts;
  var num_identicons = 100;

  var texcoords = texcoord(
    opts.rows,
    opts.columns,
    textures,
    num_identicons
  );

  self._draw(self._buffer.position, self._buffer.texcoords(texcoords), self._buffer.color(expanded_colors));
};

module.exports = Pixels;
