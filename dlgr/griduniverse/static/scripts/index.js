var parse = require("parse-color");
var isnumber = require("is-number");
var isstring = require("is-string");
var isarray = require("is-array");
var convert = require("./util/convert");
var layout = require("./util/layout");
var texcoord = require("./util/texcoord");
var range = require("./util/range");

function Pixels(data, textures, opts) {
  if (!(this instanceof Pixels)) return new Pixels(data, textures, opts);
  var self = this;
  opts = opts || {};

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
    2 * opts.padding / width,
    2 * opts.size / width,
    width / height
  );

  var positions = layout(
    opts.rows,
    opts.columns,
    2 * opts.padding / width,
    2 * opts.size / width,
    width / height
  );

  var regl = require("regl")(canvas);

  var all_textures = [
    regl.texture({
      width: 1,
      height: 1,
      data: [
        255, 255, 255, 255,
      ]
    })
  ]

  var texture_uniforms = {};
  for (var i=0;i<all_textures.length;i++) {
    texture_uniforms[`vtexture[${i}]`]=all_textures[i];
  }

  var texture_ids = range(0, all_textures.length-1);
  var squares = regl({
    vert: `
    precision mediump float;
    attribute vec2 position;
    attribute vec2 texcoords;
    attribute vec3 color;
    attribute float textureIndex;
    varying vec3 vcolor;
    varying vec2 v_texcoords;
    varying float v_textureIndex;
    void main() {
      gl_PointSize = float(${opts.size});
      gl_Position = vec4(position.x, position.y, 0.0, 1.0);
      v_texcoords = texcoords;
      vcolor = color;
      v_textureIndex = textureIndex;
    }
    `,
    frag: `
    precision mediump float;
    varying vec3 vcolor;
    varying vec2 v_texcoords;
    varying float v_textureIndex;
    uniform sampler2D vtexture[${all_textures.length}];
    void main() {
      vec4 texture;
      int textureIndex = int(v_textureIndex);
      ${texture_ids.map(id => `if (textureIndex == ${id}) {
        texture = texture2D(vtexture[${id}], v_texcoords);
      }`).join('')}
      gl_FragColor = texture * vec4(vcolor.r, vcolor.g, vcolor.b, 1.0);
    }
    `,
    attributes: { position: regl.prop("position"), texcoords: regl.prop("texcoords"), color: regl.prop("color"), textureIndex: regl.prop("textureIndex")},
    primitive: "triangles",
    count: colors.length * 6,
    uniforms: texture_uniforms
  });

  var buffer = { position: regl.buffer(positions), texcoords: regl.buffer(texcoords), color: regl.buffer(colors), textureIndex: regl.buffer(textures)  };

  var draw = function(positions, texcoords, colors, textureIndex) {
    regl.clear({ color: opts.background.concat([ 1 ]) });
    squares({ position: positions, texcoords: texcoords, color: colors, textureIndex: textureIndex });
  };

  draw(buffer.position, buffer.texcoords, buffer.color, buffer.textureIndex);

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
  var expanded_textures = []

  for(var i = 0; i< colors.length;++i){
    for(var n = 0; n<6;++n) {
      expanded_colors.push(colors[i]);
      expanded_textures.push(textures[i]);
    }
  }
  self._draw(self._buffer.position, self._buffer.texcoords, self._buffer.color(expanded_colors), self._buffer.textureIndex(expanded_textures));
};

module.exports = Pixels;
