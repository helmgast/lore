from app import app, db
from admin import admin
from api import api
from models import *
from views import *
from world import world

admin.setup()
api.setup()
app.register_blueprint(world, url_prefix='/world')
print world.root_path

if __name__ == '__main__':
    create_tables()
    app.run(debug=True) # Debug will reload code automatically, so no need to restart server