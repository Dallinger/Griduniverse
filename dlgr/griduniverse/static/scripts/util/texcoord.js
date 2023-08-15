function texcoord(rows, columns, textureIndexes, numTextures, skipTextured) {
  var grid = [];
  var texture;
  var texture_start;
  var texture_next;
  var _ = require('lodash');

  // avoid diviion by zero
  numTextures = numTextures || 1;

  for (var i = 0; i < rows; i++) {
    for (var j = 0; j < columns; j++) {
      texture = textureIndexes[i*rows + j];
      // Don't include squares with their own textures
      if (_.isString(texture) && skipTextured) {
        continue;
      } else if (_.isString(texture)) {
        texture = 0;
      }
      texture_start = (1/numTextures)*texture;
      texture_next = texture_start + (1/numTextures);

      // Map out the full texture across the six vertices for each "square"
      grid.push([ 0, texture_start ]);
      grid.push([ 1, texture_start ]);
      grid.push([ 0, texture_next ]);

      grid.push([ 0, texture_next ]);
      grid.push([ 1, texture_start ]);
      grid.push([ 1, texture_next ]);
    }
  }

  return grid;
}


module.exports = texcoord;
