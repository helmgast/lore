import datetime

from flask_peewee.admin import Admin, ModelAdmin, AdminPanel
from flask import request
from models import *

class DBAdminPanel(AdminPanel):

    template_name = 'admin/dbadmin.html'

    def get_urls(self):
        return (
            ('/dbadmin/', self.dbadmin),
        )

    def dbadmin(self):
        import model_setup
        code = request.args.get('code', None)
        if not code or code != 'pleaseresetdb':
            return "Sorry, you need to provide valid code to reset DB"
        else:
            model_setup.setup_models()
            return 'Succsessfully resetted models!' 

    def get_context(self):
        return {}

class MessageAdmin(ModelAdmin):
    columns = ('user', 'content', 'pub_date',)
    foreign_key_lookups = {'user': 'username'}

def create_admin(app, auth):
    admin = Admin(app, auth)
    auth.register_admin(admin)
    admin.register(Relationship)
    admin.register(Message, MessageAdmin)
    admin.register(Group)
    admin.register(Article)
    admin.register(PersonArticle)
    admin.register(EventArticle)
    admin.register(PlaceArticle)
    admin.register(MediaArticle)
    admin.register(FractionArticle)
    admin.register(ArticleRelation)
    admin.register(ArticleGroup)
    admin.register(RelationType)
    admin.register(GroupMember)
    admin.register(Campaign)
    admin.register(Scene)
    admin.register(Session)
    admin.register(World)
    admin.register_panel('DB Admin', DBAdminPanel)
    admin.setup()
    return admin
