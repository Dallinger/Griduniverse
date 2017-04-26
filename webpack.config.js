var webpack = require('webpack');
var UglifyJsPlugin = webpack.optimize.UglifyJsPlugin;
var env = process.env.WEBPACK_ENV;

var plugins = [];

if (env === 'build') {
  // set NODE_ENV=production in environment,
  // which ends up reducing size of React
  plugins.push(new webpack.DefinePlugin({'process.env': {'NODE_ENV': JSON.stringify('production')}}));
  // uglify code for production
  plugins.push(new UglifyJsPlugin({minimize: true}));
}

module.exports = {
  entry: {
    bundle: './static/scripts/demo.js'
  },
  output: {
    path: __dirname + '/static',
    filename: 'scripts/bundle.js'
  },
  // use jquery from separate script tag
  externals: { jquery: 'jQuery' },
  devtool: 'source-map',
  plugins: plugins
};
