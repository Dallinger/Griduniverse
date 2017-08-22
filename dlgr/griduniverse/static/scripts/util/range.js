function range(j, k) { 
    return Array
        .apply(null, Array((k - j) + 1))
        .map(function(discard, n){ return n + j; }); 
}



module.exports = range;
