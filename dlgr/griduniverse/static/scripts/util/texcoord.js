function texcoord(rows, columns, texture_indexes, num_textures) {
  var grid = [];
  var texture;
  var texture_start;
  var texture_next;

  for (var i = 0; i < rows; i++) {
    for (var j = 0; j < columns; j++) {
      texture = texture_indexes[i*rows + j];
      texture_start = (1/num_textures)*texture;
      texture_next = texture_start + (1/num_textures);

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
