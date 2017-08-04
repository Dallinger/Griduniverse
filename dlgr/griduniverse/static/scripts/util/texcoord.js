function texcoord(rows, columns, padding, size, aspect) {
  var grid = [];

  for (var i = 0; i < rows; i++) {
    for (var j = 0; j < columns; j++) {
      grid.push([ 1, 0 ]);
      grid.push([ 1, 1 ]);
      grid.push([ 0, 0 ]);

      grid.push([ 0, 0 ]);
      grid.push([ 1, 1 ]);
      grid.push([ 0, 1 ]);

    }
  }

  return grid.reverse();
}


module.exports = texcoord;
