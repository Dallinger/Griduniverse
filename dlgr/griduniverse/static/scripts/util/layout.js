function layout(rows, columns, padding, size, aspect) {
  var grid = [];

  for (var i = 0; i < rows; i++) {
    for (var j = 0; j < columns; j++) {
      var x = -1 + aspect * (i * (padding + size) + padding);
      var y = 1 - (j * (padding + size) + padding);
      grid.push([ y, x ]);
      var x_next = x + size - padding;
      grid.push([ y, x_next ]);
      var y_next = y - size + padding;
      grid.push([ y_next, x ]);

      grid.push([ y_next, x ]);
      grid.push([ y, x_next ]);
      grid.push([ y_next, x_next ]);

    }
  }

  return grid.reverse();
}


module.exports = layout;
