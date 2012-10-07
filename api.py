from flask_peewee.rest import RestAPI, RestResource, UserAuthentication, \
    AdminAuthentication, RestrictOwnerResource

from app import app
from auth import auth
from models import User, Message, Relationship
from json import dumps

user_auth = UserAuthentication(auth)
admin_auth = AdminAuthentication(auth)

# instantiate our api wrapper, we do a subclass because we have to change 
# the api registry to support multiple functions for same model (normally only 
# allows one per model)
class MyRestAPI(RestAPI):
    def register(self, model, provider=RestResource, auth=None, allowed_methods=None):
        p = provider(self, model, auth or self.default_auth, allowed_methods)
        self._registry[p.get_api_name()] = p

api = MyRestAPI(app, default_auth=user_auth)

class UserResource(RestResource):
    exclude = ('password', 'email')

class UsernameResource(RestResource):
    fields = ('username','realname')
    def get_api_name(self):
        return 'username'
    def prepare_data(self, obj, data):
        return obj.full_string()

class MessageResource(RestrictOwnerResource):
    owner_field = 'user'
    include_resources = {'user': UserResource}

class RelationshipResource(RestrictOwnerResource):
    owner_field = 'from_user'
    include_resources = {
        'from_user': UserResource,
        'to_user': UserResource,
    }
    paginate_by = None

# register our models so they are exposed via /api/<model>/
api.register(User, UserResource, auth=admin_auth)
api.register(User, UsernameResource)
api.register(Relationship, RelationshipResource)
api.register(Message, MessageResource)

def api_json(hook, objs):
    return [dumps(api._registry[hook].serialize_object(obj)) for obj in objs]
