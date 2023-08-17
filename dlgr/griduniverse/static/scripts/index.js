var parse = require("parse-color");
var isnumber = require("is-number");
var isstring = require("is-string");
var isarray = require("is-array");
var convert = require("./util/convert");
var layout = require("./util/layout");
var texcoord = require("./util/texcoord");
var _ = require('lodash');
var pixdenticon = require("./util/pixdenticon");
var md5 = require("./util/md5");


function Pixels(data, textures, opts) {
  if (!(this instanceof Pixels)) return new Pixels(data, textures, opts);
  var self = this;
  opts = opts || {};
  this.opts = opts;
  this.textureCache = {};
  this.itemTextures = {};
  var num_identicons = 100;
  this.numTextures = num_identicons;
  var texturePromises = [];
  var texture;

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
  canvas.style.backgroundColor = '#1F1F1F';
  if (opts.root) opts.root.appendChild(canvas);

  var colors = opts.formatted ? data : convert(data);
  var texcoords = texcoord(
    opts.rows,
    opts.columns,
    textures,
    this.numTextures
  );

  this.positions = layout(
    opts.rows,
    opts.columns,
    2 * opts.padding / width,
    2 * opts.size / width,
    width / height
  );

  var regl = this.regl = require("regl")(canvas);

  // First texture in the texture map is an empty square
  var initial_texture = [];
  for (let row = 0; row < opts.size; row++) {
    let rowdata = [];
    for (let col = 0; col < opts.size; col++) {
      rowdata.push([255, 255, 255]);
    }
    initial_texture.push(rowdata);
  }

  // The next textures are the identicons
  var salt = $("#grid").data("identicon-salt");
  for (let i = 0; i < num_identicons; i++) {
    let identTexture = new pixdenticon(md5(salt + i), opts.size).render().buffer;
    for (let row = 0; row < opts.size; row++) {
      initial_texture.push(identTexture[row]);
    }
  }
  texture = regl.texture(initial_texture);


  // Now w fetch any textures needed for our items
  for (let item_id in opts.item_config) {
    let itemInfo = opts.item_config[item_id];
    let itemTexture = this.textureForItem(itemInfo);
    let itemId = itemInfo.item_id;
    if (!itemTexture) continue;
    if (itemTexture.then) {
      // If we have a promise, store the texture in the itemId -> texture map
      // when it resolves.
      texturePromises.push(itemTexture);
      itemTexture.then(function (texture) {
        self.itemTextures[itemId] = texture;
      });
    } else {
      self.itemTextures[itemId] = itemTexture;
    }
  }

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
    count: function (context, props) {
      // We don't always pass in the full position grid, when we don't we need
      // to pass in a number of vertices to render
      return props.count || colors.length * 6;
    },
    uniforms: { vtexture: texture }
  });

  self.renderItemsOfType = regl({
    vert: `
      precision mediump float;
      attribute vec2 position;
      attribute vec2 texcoords;
      varying vec2 v_texcoords;
      void main () {
        gl_PointSize = float(${opts.size});
        gl_Position = vec4(position.x, position.y, 0.0, 1.0);
        v_texcoords = texcoords;
      }`,
    frag: `
      precision mediump float;
      varying vec2 v_texcoords;
      uniform sampler2D vtexture;
      void main () {
        vec4 texture;
        gl_FragColor = texture2D(vtexture, v_texcoords);
      }`,
      attributes: {position: regl.prop("position"), texcoords: regl.prop("texcoords")},
      uniforms: {vtexture: regl.prop("texture")},
      count: function (context, props) {
        return props.count;
      }
  });

  var expanded_colors = [];
  for(let i = 0; i < colors.length; ++i){
    for(let n = 0; n < 6; ++n) {
      expanded_colors.push(colors[i]);
    }
  }

  var buffer = { position: regl.buffer(this.positions), texcoords: regl.buffer(texcoords), color: regl.buffer(expanded_colors)};

  var draw = function(positions, texcoords, colors, count) {
    regl.clear({ color: opts.background.concat([ 1 ]) });
    squares({ position: positions, texcoords: texcoords, color: colors, count: count});
  };

  draw(buffer.position, buffer.texcoords, buffer.color);

  self._buffer = buffer;
  self._draw = draw;
  self._formatted = opts.formatted;
  self.canvas = canvas;
  self.frame = regl.frame;
}

Pixels.prototype.textureForItem = function(item) {
  let imageUrl;
  let image_base = this.opts.sprites_url.replace(/\/$/, ''); // remove trailing '/'
  let sprite = item.sprite;
  // The spriteValue may contain a ':', e.g. if it's a url
  let [spriteType, ...spriteValue] = sprite.split(':');
  spriteValue = spriteValue.join(':');
  if (spriteType === "image") {
    // Anything that's not an http(s) url gets prefixed with the static dir
    if (spriteValue.indexOf('http') == 0) {
      imageUrl = spriteValue;
    } else {
      spriteValue = spriteValue.replace(/^\//, ''); // remove leading '/'
      imageUrl = image_base + '/' + spriteValue;
    }
    return this.imageTexture(imageUrl)
  } else if (spriteType === "emoji") {
    return this.emojiTexture(spriteValue);
  }
}

Pixels.prototype.imageTexture = function(imageUrl) {
  if (!imageUrl) {
    return;
  }
  let textureCache = this.textureCache;

  if (imageUrl in textureCache) {
    return textureCache[imageUrl];
  }
  return new Promise ((resolve) => {
    let image = new Image();
    image.src = imageUrl;
    image.crossOrigin = "anonymous";
    image.onload = () => {
      createImageBitmap(image).then((bitmap) => {
        // Don't recreate the texture if we already have it cached
        if (!(imageUrl in textureCache)) {
          let texture = this.regl.texture(bitmap);
          textureCache[imageUrl] = texture;
        }
        resolve(textureCache[imageUrl]);
      });
    };
  });
}

Pixels.prototype.emojiTexture = function(emoji) {
  if (!emoji) {
    return;
  }
  const opts = this.opts;
  const size = opts.size * 4; // quadruple the size for retina
  let textureCache = this.textureCache;

  if (emoji in textureCache) {
    return textureCache[emoji];
  }
  let textureCanvas = document.createElement("canvas");
  textureCanvas.style.backgroundColor = "transparent";
  textureCanvas.height = textureCanvas.width = size;
  let ctx = textureCanvas.getContext("2d");
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `${size}px serif`;
  ctx.fillText(emoji, size/2, size/2);
  let texture = this.regl.texture(textureCanvas);
  textureCache[emoji] = texture;
  return textureCache[emoji]
}

Pixels.prototype.updateItems = function(texturePositions) {
  var self = this;
  const textures = self.itemTextures;
  // We render the full texture
  const texcoords = [
    [0, 0], [1, 0], [0, 1],
    [0, 1], [1, 0], [1, 1],
  ];
  var commandArgs = [];

  for (const itemId in texturePositions) {
    let positions = texturePositions[itemId];
    let count = positions.length;
    let textureMap = [];
    // Ensure the texture maps 1:1 onto the square. There's probably a better way
    while (textureMap.length < count) {
      textureMap.push.apply(textureMap, texcoords);
    }
    commandArgs.push({
      position: positions, texcoords: textureMap, texture: textures[itemId],
      count: count
    })
  }
  if (commandArgs.length) {
    // Render each item type in batch mode
    self.renderItemsOfType(commandArgs);
  }
}

Pixels.prototype.update = function(data, textures) {
  var self = this;
  const opts = this.opts;
  var colors = self._formatted ? data : convert(data);
  var expanded_colors = [];
  var positions = [];
  var idx = 0;
  var texturePositions = {};

  // We only draw squares for which don't have a custom texture to render
  for (let i = 0; i < textures.length; i++) {
    let texture = textures[i];
    let has_texture = _.isString(texture);
    if (has_texture) {
      var texture_coords = texturePositions[texture] = (texturePositions[texture] || []);
    }
    for (let n = 0; n < 6; ++n) {
      if (has_texture) {
        texture_coords.push(self.positions[idx]);
      } else {
        expanded_colors.push(colors[i]);
        positions.push(self.positions[idx]);
      }
      idx++;
    }
  }

  var texcoords = texcoord(
    opts.rows,
    opts.columns,
    textures,
    this.numTextures,
    true
  );

  self._draw(self._buffer.position(positions), self._buffer.texcoords(texcoords), self._buffer.color(expanded_colors), texcoords.length);
  self.updateItems(texturePositions);
};

module.exports = Pixels;
