/**
 * Created by martin on 2016-10-09.
 */

// TODO
    // Remove old front images from history https://help.github.com/articles/remove-sensitive-data/
    // Add trumbowyg language file
    // Request chunks as needed rather than all at once
    // Create favicons from source https://github.com/jantimon/favicons-webpack-plugin
const path = require('path');
const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin')
const ManifestRevisionPlugin = require('manifest-revision-webpack-plugin');
const ManifestPlugin = require('webpack-manifest-plugin');
const CleanWebpackPlugin = require('clean-webpack-plugin');
const SvgStore = require('webpack-svgstore-plugin');

var merge = require('merge')

config = {
    entry: {
        app: './assets/js/app.js',
    },
    output: {
        path: './static',
        filename: '[name].bundle.js',
        // publicPath: '/'
    },
    debug: true,
    module: {
        loaders: [
            {  // Loads all CSS files and puts in style tag
                test: /\.css$/,
                loader: ExtractTextPlugin.extract("style-loader", "css-loader")
            },

            {  // Loads all less files and puts in style tag, include auto-prefix
                test: /\.less$/,
                loader: ExtractTextPlugin.extract("style-loader", "css-loader!less-loader")
            },
            // {test: /\.less$/, loader: ExtractTextPlugin.extract("style-loader", "css-loader!less-loader")},
            { // Loads all JSON files, we may encounter these in node_modules
                test: /\.json$/,
                loader: 'json-loader'
            },

            // We don't minimize images because they should be minimized online by nginx/FileAssets

            { // Loads SVG files from dependencies like bootstrap into a DataURI if less than 10kb or into a hashed svg file
                test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                include: [ path.resolve(__dirname,'node_modules')],
                loader: 'url?limit=10000&mimetype=image/svg+xml&name=[name].[sha512:hash:base64:7].[ext]'
                // loader: 'file?name=[name].[sha512:hash:base64:7].[ext]'
            },
            { // Load svgs in our asset directory into one svg sprite that's loaded from within the app.js file
                test: /\.svg$/,
                include: [ path.resolve(__dirname,'assets')],
                loader: 'svg-sprite?name=fablr-[name]!svgo'
            },
            { // Loads WOFF files into a DataURI if less than 10kb or into a hashed file
                test: /\.(woff|woff2)(\?v=\d+\.\d+\.\d+)?$/,
                loader: 'url?limit=10000&mimetype=application/font-woff&name=[name].[sha512:hash:base64:7].[ext]'
            },
            { // Loads TTF files into a DataURI if less than 10kb or into a hashed file
                test: /\.ttf(\?v=\d+\.\d+\.\d+)?$/,
                // loader: 'url?limit=10000&mimetype=application/octet-stream&name=[name].[sha512:hash:base64:7].[ext]'
                loader: 'file?name=[name].[sha512:hash:base64:7].[ext]'
            },
            { // Loads EOT files into a hashed file
                test: /\.eot(\?v=\d+\.\d+\.\d+)?$/,
                loader: 'file-loader?name=[name].[sha512:hash:base64:7].[ext]'
            },
        ]
    },
    plugins: [
        // Extracts styles into separate css files instead of inside JS
        new ExtractTextPlugin('[name].bundle.css'),

        // Prints a json manifest of all assets with hashes, which can be used to lookup current name
        new ManifestRevisionPlugin('./static/manifest.json', {
            rootAssetPath: './assets/',
            ignorePaths: ['gfx'],
            extensionsRegex: /\.(css|js|eot|ttf|woff2?)$/i
        }),

        // new webpack.optimize.CommonsChunkPlugin({
        //     name: 'common'
        // }),

    ],
    resolve: {
        modulesDirectories: ['assets/js', 'node_modules'],
        extensions: ['', '.js']
    }
}

prod_config = {
    output: {
        filename: '[name].[chunkhash].js'
    },
    plugins: [
        // Extracts styles into separate css files instead of inside JS
        new ExtractTextPlugin('[name].[chunkhash].css'),

        // Prints a json manifest of all assets with hashes, which can be used to lookup current name
        new ManifestRevisionPlugin('./static/manifest.json', {
            rootAssetPath: './assets/',
            ignorePaths: ['gfx'],
            extensionsRegex: /\.(css|js|eot|ttf|woff2?)$/i
        }),

        // Cleans the dist folder when webpack is run from start
        new CleanWebpackPlugin(['static'], {
            root: process.cwd(),
            verbose: true,
            dry: false,
            exclude: ['css', 'img', 'maintenance.html', 'styleguide.html']
        }),

        // new webpack.optimize.CommonsChunkPlugin({
        //     name: 'common'
        // }),

        new webpack.optimize.UglifyJsPlugin({
            compress: {
                warnings: false,
            },
            output: {
                comments: false,
            },
        }),
    ],
}

// Detect how npm is run and branch based on that
if (process.env.npm_lifecycle_event == 'build') {
    // Production
    module.exports = merge.recursive(true, config, prod_config)
} else {
    module.exports = config
    // console.log(config)
}