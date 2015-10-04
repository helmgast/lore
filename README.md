# FABLR
Fablr is a platform for sharing stories and fictional worlds. It's a wiki and a tool for gaming and for getting together with friends.

## LICENSE
This is a prototype project and does not yet have a license, please contact us for further info.

## PLATFORMS
Fablr is a responsive web based platform that should work equally well on desktop, tablet and mobiles (assuming modern browsers!). However, it is built with an API to supporting non-web frontends such as a mobile app.

## FRAMEWORKS
Fablr is built in Python, and we use the following frameworks (plus more):
* [Flask](http://flask.pocoo.org/): Mini-framework that provides the core HTTP functionality of taking requests, reading parameters, rendering an HTML template and responding to user.
* [MongoDB](http://www.mongodb.org/): For database we use the NoSQL MongoDB that gives us a JSON like flexible document structure rather than fixed columns à la SQL.
* [Flask-Mongoengine](http://mongoengine.org/) (package `flask.ext.mongoengine.wtf`): Comes with the automatic translation of Mongoengine Document objects (Model objects) into Forms by calling model_form() function, and also makes it easy to enhance an app with the Mongoengine layer.
* [WTForms](http://wtforms.readthedocs.org/en/1.0.5/) (package `wtforms`): a generic library for building Form objects that can parse and validate data before filling up the data model object with it.
* [Flask-WTF](https://flask-wtf.readthedocs.org/en/latest/) (package `flask.ext.wtf`): a mini library that joins the WTForms with Flask, such as automatically adding CSRF tokens (security)
* [Bootstrap](http://getbootstrap.com/): for overall CSS design, typography and Javascript components
* [jQuery](http://jquery.com/): For Javascript components.

## COMPONENTS
The Fablr app contains 4 main components that interact to create the full application, but are otherwise relatively isolated. They are implemented as Flask Blueprints. They are:
* **Social**: Contains logic for users, game groups and conversations. Here users can follow other users, set up discussions or form themselves into gaming groups.
* **Campaign**: This section allows players, mostly game masters, to manage their own campaigns, including scheduling game sessions, managing story lines and scenes, and so on.
* **World**: The biggest component for Fablr, and involves Worlds and all Articles. It can be seen as a wiki or content management system optimized for fictional worlds, and with a semantical structure such as relations between places, persons, events, and so on.
* **Tools/Generator**: This is a minor component that will hold different tools that can be of use for gamers and writers.

## ARCHITECTURE
The Flask app `Fablr` runs behind a WSGI webserver. It's URL hiearchy maps both to a REST interface support GET, POST, PUT, PATCH and DELETE as well as to a traditional rendered HTML GET and POST interface. Almost all HTML is pre-rendered on server and served to client, with minor Javascript added for usability. The general principle is that of "progressive enhancement" - the website should be readable by all types of browsers including search engines and screen readers.
* `app.py` - main app code to initialize the application and run it
* `resource.py` - our own library for simplyfing the creation of the API and request flow for typical model objects with REST like operations supported
* `model/` - contains model definitions, e.g. Article, World, User, etc.
* `controller/` - each controller is a Blueprint in Flask, and initializes the URL routes, forms and request handlers. Relies heavily on resource.py.
* `static/` - contains static assets such as js, css, etc
* `templates/` - sub-organized by blueprint, this contains all Jinja2 type HTML templates.
* `translations/` - localization files.

## SETUP FOR DEVELOPMENT
**Prerequisites**: you need to have a terminal with installed git. 

First do `git clone git@github.com:per-frojdh/raconteur.git` and cd into that directory.

Then, decide if you want to run locally using virtualenv for python or if you want to use Docker to run a containerized application.

### Virtualenv
*Running virtualenv manages your python dependencies separate from your development machine, but you still need to manage the database yourself*
1. You need to have python 2.7.5, pip and virtualenv installed. Google for instructions. Additionally, to run the database locally, you need to install mongodb 3.0 or higher.
2. Inside the directory, execute:  `virtualenv venv`. Activate it by running `source venv/bin/activate` (needs to be done every time you want to develop)
3. `pip install -r requirements.txt` (will install all dependencies)
4. Default config will use a `defaultdb` on your MongoDB localhost. If that is ok, you are done, otherwise create a local `config.py` in the fablr/ directory, and override any settings needed from `default_config.py`.

### Docker
*Running Docker means having a Virtual Machine and/or separate user space where you can run the full application, including database, with guaranteed separation from your local machine, as well as (almost) identical to the server environment*
1. Install Docker if not already [https://docs.docker.com/installation/]
2. Run a temporary database image: `docker run --name mongo -d mongo`
3. Build the image by running `docker build -t fablr .`
4. Start the image by running `docker run -it --rm --link mongo:mongo fablr` (--rm will remove the containers after exiting, skip that option if you want).

### Running locally
1. Start mongodb with `mongod`
2. If the database has not been used before, or data needs to be reset, run `python run.py reset`
3. Start the application with `python run.py` or just `./run.py`
4. Point your browser to `http://localhost:5000`

### Translating strings
1. Run `python manage.py lang_extract` to find all strings needing translations and update the translation file.
2. Search the translations/[locale]/messages.po file for strings without translations, and translate in that file according to the format.
3. Run `python manage.py lang_compile` to build the binary file that is then used to do the actual translation during runtime. (note, the message.po catalog is part of the repository, but the binary file need to be built in each place the system is running)