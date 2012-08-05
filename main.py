from app import app
from views import *
from admin import admin
from api import api
from world import world
from social import social
from generator import generator
import model_setup
import sys

admin.setup()
api.setup()
app.register_blueprint(world, url_prefix='/world')
app.register_blueprint(generator, url_prefix='/generator')
app.register_blueprint(social, url_prefix='/social')

if __name__ == '__main__':
#    world_tables()
#    social_tables()
#    generator_tables()
  if len(sys.argv) > 1 and sys.argv[1] == "reset":
    print "Resetting data models"
    model_setup.setup_models()
    exit()
  app.run(debug=True) # Debug will reload code automatically, so no need to restart server
