# RACONTEUR
Raconteur is a platform for sharing stories and fictional worlds. It's a wiki and a tool for gaming and for getting together with friends.

## LICENSE
This is a prototype project and does not yet have a license, please contact us for further info.

## PLATFORMS
Raconteur is a responsive web based platform that should work equally well on desktop, tablet and mobiles (assuming modern browsers!). However, it is built with an API to supporting non-web frontends such as a mobile app.

## FRAMEWORKS
Raconteur is built in Python, and we use the following frameworks:
* [Flask](http://flask.pocoo.org/): Mini-framework that provides the core HTTP functionality of taking requests, reading parameters, rendering an HTML template and responding to user.
* [MongoDB](http://www.mongodb.org/): For database we use the NoSQL MongoDB that gives us a JSON like flexible document structure rather than fixed columns à la SQL.
* [Flask-Mongoengine](http://mongoengine.org/) (package `flask.ext.mongoengine.wtf`): Comes with the automatic translation of Mongoengine Document objects (Model objects) into Forms by calling model_form() function, and also makes it easy to enhance an app with the Mongoengine layer.
* [WTForms](http://wtforms.readthedocs.org/en/1.0.5/) (package `wtforms`): a generic library for building Form objects that can parse and validate data before filling up the data model object with it.
* [Flask-WTF](https://flask-wtf.readthedocs.org/en/latest/) (package `flask.ext.wtf`): a mini library that joins the WTForms with Flask, such as automatically adding CSRF tokens (security)
* [Bootstrap](http://getbootstrap.com/): for overall CSS design, typography and Javascript components
* [jQuery](http://jquery.com/): For Javascript components.

## COMPONENTS
The Raconteur app contains 4 main components that interact to create the full application, but are otherwise relatively isolated. They are implemented as Flask Blueprints. They are:
* **Social**: Contains logic for users, game groups and conversations. Here users can follow other users, set up discussions or form themselves into gaming groups.
* **Campaign**: This section allows players, mostly game masters, to manage their own campaigns, including scheduling game sessions, managing story lines and scenes, and so on.
* **World**: The biggest component for Raconteur, and involves Worlds and all Articles. It can be seen as a wiki or content management system optimized for fictional worlds, and with a semantical structure such as relations between places, persons, events, and so on.
* **Tools/Generator**: This is a minor component that will hold different tools that can be of use for gamers and writers.

## ARCHITECTURE
The Flask app `raconteur` runs behind a WSGI webserver. It's URL hiearchy maps both to a REST interface support GET, POST, PUT, PATCH and DELETE as well as to a traditional rendered HTML GET and POST interface. Almost all HTML is pre-rendered on server and served to client, with minor Javascript added for usability. The general principle is that of "progressive enhancement" - the website should be readable by all types of browsers including search engines and screen readers.
* `raconteur.py` - main app code to initialize the application and run it
* `resource.py` - our own library for simplyfing the creation of the API and request flow for typical model objects with REST like operations supported
* `model/` - contains model definitions, e.g. Article, World, User, etc.
* `controller/` - each controller is a Blueprint in Flask, and initializes the URL routes, forms and request handlers. Relies heavily on resource.py.
* `static/` - contains static assets such as js, css, etc
* `templates/` - sub-organized by blueprint, this contains all Jinja2 type HTML templates.
* `test_data/` - test input data to prefill the database with when calling python app.py reset

## SETUP
**Prerequisites**: you need to have a terminal with installed git, python 2.7.5, mongodb and virtualenv.
1. `git clone https://github.com/ripperdoc/raconteur.git`
2. Create a new virtualenv, activate it and then cd into the new raconteur directory
3. `python setup.py develop` (will install all dependencies)
4. Create a file named `config.cfg` in the raconteur root, and write the following into it. Make sure to change NAMEOFYOURDB and SECRETPHRASE into something that you only use locally!
```
MONGODB_SETTINGS = {'DB':'NAMEOFYOURDB'}
SECRET_KEY = 'SECRETPHRASE'
```

### Running
1. Start mongodb with `mongod`
2. If the database has not been used before, or data needs to be reset, run `python app.py reset`
3. Start the application with `python app.py`
4. Point your browser to `localhost:5000`