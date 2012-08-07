import datetime
from flask import request, redirect

from flask_peewee.admin import Admin, ModelAdmin, AdminPanel
from flask_peewee.filters import QueryFilter

from app import app, db
from auth import auth
from models import *
from world import Article

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


admin = Admin(app, auth)


class MessageAdmin(ModelAdmin):
    columns = ('user', 'content', 'pub_date',)
    foreign_key_lookups = {'user': 'username'}

auth.register_admin(admin)
admin.register(Relationship)
admin.register(Message, MessageAdmin)
admin.register(Group)
admin.register(Article)
admin.register_panel('User stats', UserStatsPanel)
