from flask import Flask
from tasks import make_celery


flask_app = Flask('raconteur')
flask_app.config.from_pyfile('config.py')
celery = make_celery(flask_app)
