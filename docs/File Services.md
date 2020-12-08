File Services
=============

Remote file
-------------

Simply a link to a remotely hosted file, no problem.


Google Drive
------------

Probably simplest storage source to upload to, and supports pulling in from disk, remote URL and re-use of existing assets in e.g. Helmgast. The downside is you need a Google account separate from Lore, and that if you share a file from Gdrive it's unclear if the URL can be publically accessed.

Downside is that large files on Google may get stopped from downloading.


Cloudinary
----------

Can upload from any user, into a shared repository. Could allow re-use of files from that storage (unclear if supported). 


Mongo GridFS
------------

Messier to deal with (upload,)


## Types of file

/static/ - uploaded by web dev or by build script
/upload/:topic_path/file.png - uploaded by users

## Authorization

Some files should require authorization to be accessed. Files on Cloudinary are inherently public (?). 