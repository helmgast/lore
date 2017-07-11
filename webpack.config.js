/**
 * Created by martin on 2016-10-09.
 */

// TODO Remove old front images from history https://help.github.com/articles/remove-sensitive-data/
// TODO Add trumbowyg language file
// TODO Request chunks as needed rather than all at once
// TODO Create favicons from source https://github.com/jantimon/favicons-webpack-plugin

const path = require('path');
const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const ManifestPlugin = require('webpack-manifest-plugin');
const CleanWebpackPlugin = require('clean-webpack-plugin');
const SpritePlugin = require('svg-sprite-loader/plugin');

var merge = require('merge')

config = {
    entry: {
        app: path.resolve(__dirname, 'assets/js/app.js'),
    },
    output: {
        path: path.resolve(__dirname, 'static/dist'),
        filename: '[name].[chunkhash].js',
        publicPath: '/static/dist/'
    },
    module: {
        rules: [
            {  // Loads all CSS files and puts in style tag
                test: /\.css$/,
                use: ExtractTextPlugin.extract({
                    fallback: "style-loader",
                    use: "css-loader",
                }),
            },

            {  // Loads all less files and puts in style tag, include auto-prefix
                test: /\.less$/,
                use: ExtractTextPlugin.extract({
                    fallback: "style-loader",
                    use: ['css-loader', 'less-loader'],
                }),
            },

            // We don't minimize images because they should be minimized online by nginx/FileAssets

            { // Loads SVG files from dependencies like bootstrap into a DataURI if less than 10kb or into a hashed svg file
                test: /\.svg(\?v=\d+\.\d+\.\d+)?$/,
                include: [path.resolve(__dirname, 'node_modules')],
                use: [
                    {
                        loader: 'url-loader',
                        options: {
                            limit: 8192,
                            name: '[name].[sha512:hash:base64:7].[ext]'
                        }
                    }
                ],
            },
            { // Load svgs in our asset directory into one svg sprite that's loaded from within the app.js file
                test: /\.svg$/,
                include: [path.resolve(__dirname, 'assets')],
                use: [
                    'svg-sprite-loader',
                    'svgo-loader'
                ]
            },
            { // Loads WOFF files into a DataURI if less than 10kb or into a hashed file
                test: /\.(eot|ttf|woff|woff2)(\?v=\d+\.\d+\.\d+)?$/,
                use: [
                    {
                        loader: 'url-loader',
                        options: {
                            limit: 8192,
                            name: '[name].[sha512:hash:base64:7].[ext]'
                        }
                    }
                ]
            }
        ]
    },
    plugins: [
        // Extracts styles into separate css files instead of inside JS
        new ExtractTextPlugin('[name].[chunkhash].bundle.css'),
        new SpritePlugin(),
        new ManifestPlugin({
            publicPath: 'dist/' // prefixed with 'static/' by flask already
        }),
        new CleanWebpackPlugin(['static/dist'])

    ],
    resolve: {
        modules: ['assets/js', 'node_modules'],
    }
}

module.exports = config

