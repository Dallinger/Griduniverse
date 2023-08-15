function texcoord(rows, columns, texture_indexes, num_textures, skip_items) {
  var grid = [];
  var texture;
  var texture_start;
  var texture_next;
  var _ = require('lodash');

  // avoid diviion by zero
  num_textures = num_textures || 1;

  for (var i = 0; i < rows; i++) {
    for (var j = 0; j < columns; j++) {
      texture = texture_indexes[i*rows + j];
      // Don't include squares with their own textures
      if (_.isString(texture) && skip_items) {
        continue;
      } else if (_.isString(texture)) {
        texture = 0;
      }
      texture_start = (1/num_textures)*texture;
      texture_next = texture_start + (1/num_textures);

      // Upper left triangle in texture map
      grid.push([ 0, texture_start ]);
      grid.push([ 1, texture_start ]);
      grid.push([ 0, texture_next ]);
      // Lower right triangle in texture map
      grid.push([ 0, texture_next ]);
      grid.push([ 1, texture_start ]);
      grid.push([ 1, texture_next ]);
    }
  }

  return grid;
}


module.exports = texcoord;
