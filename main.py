from app import app, db
from admin import admin
from api import api
from models import *
from views import *
from world import world, create_tables as world_tables
from social import social, create_tables as social_tables
import model_setup

admin.setup()
api.setup()
app.register_blueprint(world, url_prefix='/world')
app.register_blueprint(social, url_prefix='/social')

if __name__ == '__main__':
    #world_tables()
    #social_tables()
    model_setup.setup_models()
    app.run(debug=True) # Debug will reload code automatically, so no need to restart server