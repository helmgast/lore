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
const CleanWebpackPlugin = require('clean-webpack-plugin');
// const SpritePlugin = require('svg-sprite-loader/plugin');
const SVGSpritemapPlugin = require('svg-spritemap-webpack-plugin');
const WebpackAssetsManifest = require('webpack-assets-manifest');


function getConfig(devMode) {
    return {
    devtool: devMode ? 'cheap-module-eval-source-map' : '',
    entry: {
        app: path.resolve(__dirname, 'assets/js/app.js'),
    },
    output: {
        path: path.resolve(__dirname, devMode ? 'static/dev' : 'static/dist'),
        filename: devMode ? '[name].js' : '[name].[contenthash:8].js',
        chunkFilename: devMode ? '[id].js' : '[id].[contenthash:8].js',
        // This will be prepended to URLs printed at build-time (into e.g. css files). At runtime, we will use dynamic
        // variable from server set in app.js.
        publicPath: devMode ? '/static/dev/': '/static/dist/'
    },
    module: {
        rules: [
            {  // Loads all CSS files and puts in style tag
                test: /\.css$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    "css-loader"
                  ]
            },

            {  // Loads all less files and puts in style tag, include auto-prefix
                test: /\.less$/,
                use: [
                    MiniCssExtractPlugin.loader,
                    "css-loader",
                    "less-loader"
                  ]
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
                            name: devMode ? '[name].[ext]' : '[name].[hash:8].[ext]'
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
                            name: devMode ? '[name].[ext]' : '[name].[hash:8].[ext]'
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
            filename: devMode ? '[name].css' : "[name].[contenthash:8].css",
          }),
        // new SpritePlugin(),
        new SVGSpritemapPlugin('assets/gfx/*.svg', {
            output: {filename: devMode ? 'spritemap.svg' : 'spritemap.[contenthash].svg'},  // doesn't support short hash
            sprite: {prefix: 'lore-'}
        }),
        // Have also tried webpack-manifest-plugin and assets-webpack-plugin, not giving exactly what we need
        new WebpackAssetsManifest({
            writeToDisk: true, 
            publicPath: devMode ? 'dev/': 'dist/',  // No static prefix as it's added by Lore server static calls
            output: path.resolve(__dirname, 'static/manifest.json')
        }),
        new CleanWebpackPlugin(),

    ],
    resolve: {
        modules: ['assets/js', 'node_modules'],
    }
    }
}

module.exports = (env, argv) => {
    console.log("MODE "+argv.mode);
    return getConfig(argv.mode !== 'production');
}


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
//             prefix: 'lore-',
//         }),
//     ],
//     resolve: {
//         modules: ['assets/js', 'node_modules'],
//     }
// }

// module.exports = config