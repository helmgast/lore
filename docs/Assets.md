# Assets

Assets is a seemingly simple area that can get very complicated. This is due to the desire to optimize their footprint and flexibility of storage and therefore the desire to have an automated process to add assets.
In Lore there are `static` assets, and `dynamic` assets. Static assets come with the code, and dynamic assets
come from the database (even if they might be served from some other URL).

To optimize static assets, like JS, CSS, SVG we may want to:

1. Minify and combine assets into combined files (or spritemaps for SVG)
2. Give a name with a hash that allows us to cache them as long as possible. When a file changes, the hash and file name changes. This gives us maximum "cachability".
3. Load the files only when needed, which depends on logic on both backend and frontend

It is very cumbersome to manually do above steps, so we need an automated tool. This is done by Webpack, a very common tool for JS-based sites. It is a pre-processor that runs a "build" stage on all assets, which means it starts with some files as entrypoints, and then scans all that file and it's dependencies for references to sources and assets. Then all of these, depending on different plugins, will be combined and processed as above. In a production setting, out comes a `dist` folder that contains files like `app.6a266d7b.js`.

Webpack can be complex to configure, but apart from that, assets are tricky because we don't have shared information between build-time and run-time, as well as between frontend and backend. To give an example, we might have an SVG file with icons. It's source might come from `assets/icons.svg`. Webpack outputs it to `statis/dist/icons.ab16ba.svg`. A JS file that references the SVG, cannot know that the new path with the hash, so it depends on that Webpack also replaces all references to `icons.svg` with the new path.

But if we instead references the SVG file in backend code, it runs in Python and uses a different method (url_for) to generate an URL to a static resource. Webpack cannot go through the Python code or templates, so we need to tell the backend where the static resources are. This is done through a `manifest.json` file that show what files were called originally and what they are called after build.

To make the problem trickier, we may not be enough with relative URLs. Assets might be on a different server, and we might not be able to hard-code this. For example, when developing, Lore runs on `lore.test` but on production it runs on `lore.pub`. To sum up, the same file can be referenced in many ways:

- `assets/icons.svg` source location, and relative reference from other assets
- `static/dist/icons.ab16ba.svg` built location, what webpack might
- `dist/icons.ab16ba.svg` built location, as references in manifest.json (because the backend will prepend static automatically)
- `https://lore.test/static/dist/icons.ab16ba.svg` non-production, built absolute reference
- `https://lore.pub/static/dist/icons.ab16ba.svg` production, built absolute reference

## Asset linking

Types of assets to link to:

- Raw images `[domain]/asset/image/filename.ext`. Returns an original image asset.
- Resized images `[domain]/asset/thumb/size-filename.ext`. Returns a resized image asset. Size is a variable that the backend determines dimensions of, e.g. wide|center|side|logo
- File link `[domain]/asset/link/filename.ext`
- File download `[domain]/asset/file/filename.ext`

## File handling re-design

- Make all files be attached to a specific Article (or World, Publisher, Product, etc). In this way, there is no general storage of files and much simpler management.
- A FileAsset simply contain an URL to a remote file “original”. Built-in to it is the ability to represent the file as thumbnail and various crop formats, by generating URLs based on various parameters. These formats are defined by Lore Design System and are underneath the hood using Cloudinary parameters. But if we change to something else than Cloudinary, we will not need to change the way the FileAssets are used anywhere.
- As the FileAsset also may be something else than an image, we can have built in logic to create a thumbnail or similar even if it’s a PDF (Cloudinary has this feature).
- We create a redirect location that makes it easy to hide original URL source for files, e.g. if they are in Gdrive, Cloudinary or S3. This is under publisher domain, to avoid sharing links like fablr.co or lore.pub.
- However, as we generate thumbnails, we wan’t to avoid losing performance by jumping through a redirect, so we can just generate them directly on a server using a macro, which also includes img srcset.
- In the editor, the simplest way might be to see all attachments on the side and to be able to drag and drop them into the document. When you do that, you should get an option on what crop format to apply.
- To pick from a library of media files, simply use a Google Drive picker. This means it’s easy for Helmgast creators to re-use images directly and avoid having to build two separate libraries. For other users, they won’t necessarily have access to our library but may of course request so.

# File services

File services are different backends that can host an asset for Lore.

## Remote file

Simply a link to a remotely hosted file, no problem, but also means something else has to manage the full state of the asset.


## Google Drive

Probably simplest storage source to upload to, and supports pulling in from disk, remote URL and re-use of existing assets in e.g. Helmgast. The downside is you need a Google account separate from Lore, and that if you share a file from Gdrive it's unclear if the URL can be publically accessed.

Downside is that large files on Google may get stopped from downloading.


## Cloudinary

Can upload from any user, into a shared repository. Could allow re-use of files from that storage (unclear if supported). 

## Mongo GridFS

Messier to deal with (upload,)


### Types of file

/static/ - uploaded by web dev or by build script
/upload/:topic_path/file.png - uploaded by users

### Authorization

Some files should require authorization to be accessed. Files on Cloudinary are inherently public (?). 