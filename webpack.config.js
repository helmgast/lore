/**
 * Created by martin on 2016-10-09.
 */

// TODO Remove old front images from history https://help.github.com/articles/remove-sensitive-data/
// TODO Add trumbowyg language file
// TODO Request chunks as needed rather than all at once
// TODO Create favicons from source https://github.com/jantimon/favicons-webpack-plugin

// A treatise on static files
// As we use a fixed domain for static files (e.g. our own CDN) we need absolute URLs for assets
// However, we will run this code sometimes with a development domain, sometimes production, so we cannot
// hardcode it. This is what happens:
// output.publicPath sets the path to add on URLs printed into bundles. This is not full URL, but absolute path.
// This is ok, because URLs in CSS files will be relative to where they were served, which will be from the CDN
// domain whatever it is.
// ManifestPlugin creates a manifest using the same public path as above. But here we will use url_for on server
// so we actually need to strip the /static/ prefix as it will be added again in Flask.
// In the generated JS file, we can dynamically change the public path first thing, by using a variable provided
// by the server as a Javascript global variable.
// Complicated, no?

const path = require('path');
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const ManifestPlugin = require('webpack-manifest-plugin');
const CleanWebpackPlugin = require('clean-webpack-plugin');
// const SpritePlugin = require('svg-sprite-loader/plugin');
const SVGSpritemapPlugin = require('svg-spritemap-webpack-plugin');


config = {
    mode: 'development',
    entry: {
        app: path.resolve(__dirname, 'assets/js/app.js'),
    },
    output: {
        path: path.resolve(__dirname, 'static/dist'),
        filename: '[name].[chunkhash].js',
        // This will be prepended to URLs printed at build-time (into e.g. css files). At runtime, we will use dynamic
        // variable from server set in app.js.
        publicPath: '/static/dist/'
    },
    module: {
        rules: [
            {  // Loads all CSS files and puts in style tag
                test: /\.css$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    "css-loader"
                  ]
                // use: ExtractTextPlugin.extract({
                //     fallback: "style-loader",
                //     use: "css-loader",
                // }),
            },

            {  // Loads all less files and puts in style tag, include auto-prefix
                test: /\.less$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    "css-loader",
                    "less-loader"
                  ]
                // use: ExtractTextPlugin.extract({
                //     fallback: "style-loader",
                //     use: ['css-loader', 'less-loader'],
                // }),
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
            // { // Load svgs in our asset directory into one svg sprite that's loaded from within the app.js file
            //     test: /\.svg$/,
            //     include: [path.resolve(__dirname, 'assets')],
            //     use: [
            //         'svg-sprite-loader',
            //         'svgo-loader'
            //     ]
            // },
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
        new MiniCssExtractPlugin({
            // Options similar to the same options in webpackOptions.output
            // both options are optional
            // filename: "[name].[chunkhash].bundle.css",
            chunkFilename: "[name].[hash].css"
          }),
        // new ExtractTextPlugin('[name].[chunkhash].bundle.css'),
        // new SpritePlugin(),
        new SVGSpritemapPlugin({
            src: 'assets/gfx/*.svg',
            filename: 'spritemap.[contenthash].svg',
            prefix: 'fablr-',
        }),
        new ManifestPlugin({
            map: function(o){o.path = o.path.replace('/static/',''); return o}}),

        new CleanWebpackPlugin(['static/dist'])

    ],
    resolve: {
        modules: ['assets/js', 'node_modules'],
    }
}

module.exports = config

// const SVGSpritemapPlugin = require('svg-spritemap-webpack-plugin');
// const path = require('path');

// config = {
//     mode: 'development',
//     entry: {
//         app: [path.resolve(__dirname, 'assets/js/test.js')],
//     },
//     output: {
//         path: path.resolve(__dirname, 'static/dist'),
//         filename: '[name].[chunkhash].js',
//         publicPath: '/static/dist/'
//     },
//     plugins: [
//         new SVGSpritemapPlugin({
//             src: 'assets/gfx/*.svg',
//             filename: 'spritemap.[contenthash].svg',
//             prefix: 'fablr-',
//         }),
//     ],
//     resolve: {
//         modules: ['assets/js', 'node_modules'],
//     }
// }

// module.exports = config