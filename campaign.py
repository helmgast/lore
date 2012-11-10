from flask import request, redirect, url_for, render_template, Blueprint, flash
from auth import auth
from flask_peewee.utils import get_object_or_404
from wtfpeewee.orm import model_form
from models import Group, GroupMember, Campaign, Session, Scene, GROUP_MASTER
from datetime import datetime, timedelta, date, time
from resource import ResourceHandler
from json import loads

campaign = Blueprint('campaign', __name__, template_folder='templates')

class SessionHandler(ResourceHandler):
    model_class = Session
    form_class = model_form(model_class, exclude=[])
    
    def get_form(self, op):
        if op=='new':
            # set start time to tomorrow 18.00 if no play_start given, else set to 18.00 of the date given
            if request.args.has_key('play_start'):
                play_start = datetime.strptime(request.args.get('play_start'),'%Y-%m-%d') + timedelta(hours=18)
            else:
                play_start = datetime.combine(date.today()+timedelta(days=1), time(hour=18))
            play_end = play_start + timedelta(hours=5) # end 5 hours later
            return self.form_class(obj=self.instance, play_start=play_start, play_end=play_end)
        else:
            return ResourceHandler.get_form(self, op)

    def allowed(op, user, instance=None):
        if user:
            if op=='view' or op=='new':
                return True
            else:
                gms = GroupMember.select().where(GroupMember.group == instance.campaign.group, GroupMember.member == user)
                return (gms.count() == 1) # user is in group and can edit
        return False

class CampaignHandler(ResourceHandler):
    model_class = Campaign
    form_class = model_form(model_class, exclude=['slug'])

    def prepare_get(self, op):
        if op == 'edit' or op=='new':
            mastered_groups = Group.select().join(GroupMember).where(GroupMember.member == self.user, GroupMember.status == GROUP_MASTER)
            self.form.group.query = mastered_groups # set only mastered groups into the form select field
            self.scenes = Scene.select().where(Scene.campaign == self.instance, Scene.parent >> None).order_by(Scene.order.asc()) # >> None means 'is null'
            self.sceneform = SceneHandler.form_class()

    def after_post(self, op):
        if request.form.has_key('scene_tree'):
            scene_tree = loads(request.form.get('scene_tree'))
            print scene_tree
            self.instance.load_scene_tree(scene_tree)

    def allowed(op, user, instance=None):
        if user:
            if op=='view' or op=='new':
                return True
            else:
                gms = GroupMember.select().where(GroupMember.group == instance.group, GroupMember.member == user, GroupMember.status == GROUP_MASTER)
                return (gms.count() == 1) # user is master in group and can edit
        return False

class SceneHandler(ResourceHandler):
    model_class = Scene
    form_class = model_form(model_class, exclude=['order', 'parent', 'campaign'])

    def allowed(op, user, instance=None):
        if user:
            if op=='view' or op=='new':
                return True
            else:
                gms = GroupMember.select().where(GroupMember.group == instance.campaign.group, GroupMember.member == user, GroupMember.status == GROUP_MASTER)
                return (gms.count() == 1) # user is master in group and can edit
        return False

@campaign.route('/')
def index():
    return campaigns()

@campaign.route('/sessions/')
@auth.login_required
def sessions():
    user = auth.get_logged_in_user()
    member_in_groups = Group.select().join(GroupMember).where(GroupMember.member == user)
    sessions = Session.select().join(Campaign).where(Campaign.group << member_in_groups)
    return render_template('campaign/sessions.html', sessions=sessions)

@campaign.route('/sessions/new', methods=['GET', 'POST'])
@auth.login_required
def session_new():
    rh = SessionHandler('campaign/session_page.html')
    return rh.handle_request('new')

@campaign.route('/sessions/<id>', methods=['GET', 'POST'])
@auth.login_required
def session_detail(id):
    rh = SessionHandler('campaign/session_page.html', get_object_or_404(Session, Session.id == id))
    return rh.handle_request('edit')

@campaign.route('/campaigns/')
def campaigns():
    campaigns = Campaign.select()
    return render_template('campaign/campaigns.html', campaigns=campaigns)

@auth.login_required
@campaign.route('/campaigns/new', methods=['GET', 'POST'] )
def campaign_new():
    rh = CampaignHandler('campaign/campaign_page.html')
    return rh.handle_request('new')

@campaign.route('/campaigns/<slug>', methods=['GET', 'POST'] )
def campaign_detail(slug):
    rh = CampaignHandler('campaign/campaign_page.html', get_object_or_404(Campaign, Campaign.slug == slug))
    return rh.handle_request('edit')

@auth.login_required
@campaign.route('/campaigns/<slug>/scenes/new', methods=['GET', 'POST'] )
def scene_new(slug):
    rh = SceneHandler('campaign/scene_page.html')
    return rh.handle_request('new')

@campaign.route('/campaigns/<slug>/scenes/<id>', methods=['GET', 'POST'] )
def scene_detail(slug, id):
    rh = SceneHandler('campaign/scene_page.html', get_object_or_404(Scene, Scene.id == id))
    return rh.handle_request('edit')

@auth.login_required
@campaign.route('/campaigns/<slug>/scenes/<id>/delete', methods=['GET', 'POST'] )
def scene_delete(slug, id):
    rh = SceneHandler('campaign/scene_page.html', get_object_or_404(Scene, Scene.id == id))
    return rh.handle_request('delete')


