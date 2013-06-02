import datetime

from flask_peewee.admin import Admin, ModelAdmin, AdminPanel
from models import *

class UserStatsPanel(AdminPanel):
    template_name = 'admin/user_stats.html'
    
    def get_context(self):
        last_week = datetime.datetime.now() - datetime.timedelta(days=7)
        signups_this_week = User.filter(join_date__gt=last_week).count()
        messages_this_week = Message.filter(pub_date__gt=last_week).count()
        return {
            'signups': signups_this_week,
            'messages': messages_this_week,
        }

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
    admin.register(ArticleRelation)
    admin.register(RelationType)
    admin.register(GroupMember)
    admin.register(World)
    admin.register_panel('User stats', UserStatsPanel)
    admin.setup()
    return admin
