/**
 * Derived from Identicon.js 2.3.1
 * http://github.com/stewartlord/identicon.js
 *
 * Copyright 2017, Stewart Lord and Dallinger Contributors
 * Released under the BSD license
 * http://www.opensource.org/licenses/bsd-license.php
 */


var Identicon = function(hash, size, options){
    if (typeof(hash) !== 'string' || hash.length < 15) {
        throw 'A hash of at least 15 characters is required.';
    }

    this.defaults = {
        background: [240, 240, 240, 255],
        margin:     0.08,
        size:       64,
        saturation: 0.7,
        brightness: 0.5,
        format:     'pixels'
    };

    this.options = typeof(options) === 'object' ? options : this.defaults;

    this.hash        = hash
    this.background  = [128, 128, 128];
    this.foreground  = [255, 255, 255];
    this.size        = size;
};

Identicon.prototype = {
    background: null,
    foreground: null,
    hash:       null,
    margin:     null,
    size:       null,
    format:     null,

    image: function(){
        return new Pixels(this.size, this.foreground, this.background)
    },

    render: function(){
        var image      = this.image(),
            size       = this.size,
            baseMargin = Math.floor(size * this.margin),
            cell       = Math.floor((size - (baseMargin * 2)) / 5),
            margin     = Math.floor((size - cell * 5) / 2),
            bg         = this.background,
            fg         = this.foreground;

        // the first 15 characters of the hash control the pixels (even/odd)
        // they are drawn down the middle first, then mirrored outwards
        var i, color;
        for (i = 0; i < 15; i++) {
            color = parseInt(this.hash.charAt(i), 16) % 2 ? bg : fg;
            if (i < 5) {
                this.rectangle(2 * cell + margin, i * cell + margin, cell, cell, color, image);
            } else if (i < 10) {
                this.rectangle(1 * cell + margin, (i - 5) * cell + margin, cell, cell, color, image);
                this.rectangle(3 * cell + margin, (i - 5) * cell + margin, cell, cell, color, image);
            } else if (i < 15) {
                this.rectangle(0 * cell + margin, (i - 10) * cell + margin, cell, cell, color, image);
                this.rectangle(4 * cell + margin, (i - 10) * cell + margin, cell, cell, color, image);
            }
        }

        return image;
    },

    rectangle: function(x, y, w, h, color, image){
        var i, j;
        for (i = x; i < x + w; i++) {
            for (j = y; j < y + h; j++) {
                image.buffer[j][i] = color;
            }
        }
    }

};

var Pixels = function(size){
    this.buffer = [];
    for (i = 0; i < size; i++) {
        var row = []
        for (j = 0; j < size; j++) {
            row.push([0,0,120]);
        }
        this.buffer.push(row);
    }
};

Pixels.prototype = {
    pixels:       null,

};


module.exports = Identicon;
