# LORE

Lore is a platform for creating and sharing stories and fictional worlds between printed and digital media. It's a wiki and a tool for game creators and gamers alike. It's a responsive web based platform that should work equally well on desktop, tablet and mobiles (optimized for modern browsers - above IE8). However, it is built with an API to support non-web frontends such as mobile apps.

## FRAMEWORKS

Lore's backend is built in Python, and we use the following frameworks (plus more):

* [Flask](http://flask.pocoo.org/): Mini-framework that provides the core HTTP functionality of taking requests, reading parameters, rendering an HTML template and responding to user.
* [MongoDB](http://www.mongodb.org/): For database we use the NoSQL MongoDB that gives us a JSON like flexible document structure rather than fixed columns à la SQL.
* [Flask-Mongoengine](http://mongoengine.org/) (package `flask.ext.mongoengine.wtf`): Comes with the automatic translation of Mongoengine Document objects (Model objects) into Forms by calling model_form() function, and also makes it easy to enhance an app with the Mongoengine layer.
* [WTForms](http://wtforms.readthedocs.org/en/latest/) (package `wtforms`): a generic library for building Form objects that can parse and validate data before filling up the data model object with it.
* [Flask-WTF](https://flask-wtf.readthedocs.org/en/latest/) (package `flask.ext.wtf`): a mini library that joins the WTForms with Flask, such as automatically adding CSRF tokens (security)
* [Bootstrap](http://getbootstrap.com/): for overall CSS design, typography and Javascript components
* [jQuery](http://jquery.com/): For Javascript components.

## COMPONENTS

The Lore app contains five main components that interact to create the full application, but are otherwise relatively isolated. They are implemented as Flask Blueprints. They are:

* **World**: The biggest component for Lore, and involves Worlds and all Articles. It can be seen as a wiki or content management system optimized for fictional worlds, and with a semantical structure such as relations between places, persons, events, and so on.
* **Social**: Contains logic for users, game groups and conversations. Here users can follow other users, set up discussions or form themselves into gaming groups.
* **Shop**: Contains an order system, a storefront and shopping cart and purchasing logic.
* **Campaign**: This section allows players, mostly game masters, to manage their own campaigns, including scheduling game sessions, managing story lines and scenes, and so on.

## ARCHITECTURE

The Flask app `Lore` runs behind a WSGI webserver. It's a REST based API / URL hierarchy that both offers a JSON API supporting GET, POST, PUT, PATCH and DELETE as well as to a traditional rendered HTML GET and POST interface. Almost all HTML is pre-rendered on server and served to client, with minor Javascript added for usability. The general principle is that of "progressive enhancement" - the website should be readable by all types of browsers including search engines and screen readers.

At the top of the file hierarchy we have a `lore` directory for application code, a `tests` directory for test code and `tools` for peripheral tools. Additionally, it includes the README and other main documentation, the script to start the server (`run.py`) and the package dependencies (`requirements.in` and `dev-requirements.in`).

In the `lore` folder we have the following parts of the source code:

* `app.py` - main app code to initialize the application and run it
* `model/` - contains model definitions, e.g. Article, World, User, etc.
* `api/` - each controller is a Blueprint in Flask, and initializes the URL routes, forms and request handlers. Relies heavily on resource.py.
* `api/resource.py` - our own library for simplyfing the creation of the API and request flow for typical model objects with REST like operations supported
* `templates/` - sub-organized by blueprint, this contains all Jinja2 type HTML templates.
* `translations/` - localization files.

Outside the `lore` folder we also have a `static` folder that contains generated JS, CSS and some image assets, plus a `plugins` folder that contains themes and other plugins.

## SETUP FOR DEVELOPMENT

**Prerequisites**: you need to have a terminal with installed git.

First do `git clone git@github.com:helmgast/lore.git` and cd into that directory.

Then, decide if you want to run locally using virtualenv for python or if you want to use Docker to run a containerized application.

### Frontend

Run `npm install` to install all frontend (JS, CSS) dependencies. You need [npm](https://www.npmjs.com/) installed.

Run `npm run build` to do one-time production build (which will create new versioned assets in /static/ that needs to be commited to repo)

Run `npm run watch` when developing, will continuously re-build frontend assets as they change.

### Virtualenv

*Running virtualenv manages your python dependencies in isolation from your development machine, but still needs you to manage other parts like database yourself*

1. You need to have python >3.7, pip, pip-tools and virtualenv installed. Additionally, to run the database locally, you need to install mongodb 4.0 or higher.
2. Inside the directory, execute:  `virtualenv venv`. It creates the sub-directory `venv`. Activate it by running `source venv/bin/activate` (needs to be done every time you want to develop)
3. The `requirements.in` and `dev-requirements.in` files contain the dependencies we have, with a rule to search for specific version or latest if empty. Run `pip-compile requirements.in dev-requirements.in` to build them into `requirements.txt dev-requirements.txt` that contain the actual, locked versions, similar to how `package-lock.json` works. This file guarantees that a Docker container or clone of the repo can install the exact same dependencies. Install those with `pip install -r requirements.txt` for production or `pip install -r requirements.txt dev-requirements.txt` for all.
4. In a separate terminal, run MongoDB by executing `mongod`. Default config will assume a `defaultdb` on your MongoDB localhost. If that is ok, you are done, otherwise create a local `config.py` in the `lore/` directory, and override any settings needed from `default_config.py`. `config.py` should be written without any classes.
5. Start the development server by running `flask -a run.py --debug run`. [flask command docs](http://flask.pocoo.org/docs/dev/quickstart/#debug-mode)

### Docker

*Running Docker means having a Virtual Machine and/or separate user space where you can run the full application, including database, with guaranteed separation from your local machine, as well as (almost) identical to the server environment*

1. [Install](https://docs.docker.com/installation/) Docker if not already
2. Run a temporary database image: `docker run -d --name mongo -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=pass -p 27018:27017 mongo`. Important to setup auth to keep it similar to how you'd run it in production.
3. Build the image by running `docker build -t lore .` This uses the `Dockerfile` to setup the correct dependencies and environment. Rebuild any time your code has changed.
4. Start the image by running `docker run -it --rm --link mongo:mongo lore` (--rm will remove the containers after exiting, skip that option if you want to have persistence).

(alternatively, use [docker-compose](https://docs.docker.com/compose/) and create a `docker-compose.yml' file that can include both database, application and other services)

### Debugging

There are 3 levels of debugging that can be done.
1. Run the Flask development server on local machine, started with `flask run` or from your IDE. It will need a MongoDB instance running, and can be reached in browser using localhost:5000 . Note, this will NOT easily support the multi-domain behaviour of Lore.
2. Run the docker-compose file to setup an Nginx reverse proxy. This will let you run as close to production environment as possible, including with (self-signed) HTTPS and multiple domains. Lore listens to lore.test by default. You need to create local pointers to lore.test and other .test domains (for publishers) in /etc/hosts or using local DNS. When you do this, you can point Nginx to your Flask development server as started above, where you can debug and set breakpoints.
3. If you don't need to set breakpoints, just run the full docker-compose file to start the full environment from Docker. This will run lore on the full configuration.

### Localization

Lore defaults to English but comes with a Swedish localization as well, and more can be
added. If you add or change new messages to translate, see below:

1. Run `python manage.py lang_extract` to find all strings needing translations and update the translation file.
2. Search the lore/translations/[locale]/messages.po file for strings without translations, and translate in that file according to the format.
3. Run `python manage.py lang_compile` to build the binary file that is then used to do the actual translation during runtime. (note, the binary file is not added to repository so you need to compile the language on each update and host). If you run Docker, the language will be automatically compiled at Docker build time.

### Deployment in production

For deployment on a production server, it's recommended to use a Docker setup with `gunicorn` as WSGI server and potentially `nginx` as reverse proxy and cache. This repository contain no deployment details or settings for security, see separate repository.

#### Static assets

To keep it simple, static assets will be served either by flasks `static` route or by `FileAssets`. To work well in production, you need to have a cache in front of these - we use nginx. Setup nginx as proxy cache, and it will serve files much more efficiently (except at first request).

If you do not use a cache in front, you could move/copy the static assets from /static folder to a place where a more efficient web server can serve them. But this would not cover the `FileAsset` case as they need to be served from Lore as it uses Mongonegine as the file backend, not a file system.
