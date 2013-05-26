from flask import request, redirect, url_for, render_template, Blueprint, flash
from raconteur import auth
from flask_peewee.utils import get_object_or_404
from wtfpeewee.orm import model_form
from models import Group, GroupMember, Campaign, Session, Scene, GROUP_MASTER
from datetime import datetime, timedelta, date, time
from resource import ResourceHandler, ResourceRequest
from json import loads

campaign = Blueprint('campaign', __name__, template_folder='templates')

class SessionHandler(ResourceHandler):
    def get_resource_instance(self, op, user, instance=None):
        if op==ResourceHandler.NEW:
            # set start time to tomorrow 18.00 if no play_start given, else set to 18.00 of the date given
            if request.args.has_key('play_start'):
                play_start = datetime.strptime(request.args.get('play_start'),'%Y-%m-%d') + timedelta(hours=18)
            else:
                play_start = datetime.combine(date.today()+timedelta(days=1), time(hour=18))
            play_end = play_start + timedelta(hours=5) # end 5 hours later
            form = self.form_class(obj=self.instance, play_start=play_start, play_end=play_end)
        else:
            form = self.form_class(obj=instance) if (op==self.EDIT or op==self.NEW) else None
        return ResourceRequest(op, form, instance)

    def allowed(self, op, user, instance=None):
        if user:
            if op==ResourceHandler.VIEW or op==ResourceHandler.NEW:
                return True
            else:
                gms = GroupMember.select().where(GroupMember.group == instance.campaign.group, GroupMember.member == user)
                return (gms.count() == 1) # user is in group and can edit
        return False

sessionhandler = SessionHandler(
        Session,
        model_form(Session, exclude=[]),
        'campaign/session_page.html.html',
        'campaign.session_detail')

class CampaignHandler(ResourceHandler):
    def get_resource_instance(self, op, user, instance=None):
        form = self.form_class(obj=instance) if (op==ResourceHandler.EDIT or op==ResourceHandler.NEW) else None
        ri = ResourceRequest(op, form, instance)
        if op == ResourceHandler.EDIT or op==ResourceHandler.NEW:
            mastered_groups = Group.select().join(GroupMember).where(GroupMember.member == user, GroupMember.status == GROUP_MASTER)
            form.group.query = mastered_groups # set only mastered groups into the form select field
            ri.scenes = Scene.select().where(Scene.campaign == instance, Scene.parent >> None).order_by(Scene.order.asc()) # >> None means 'is null'
            ri.sceneform = scenehandler.form_class()
        return ri

    def get_redirect_url(self, instance):
        return url_for(self.route, slug=instance.slug)

    def after_post(self, op, user, instance=None):
        if request.form.has_key('scene_tree'):
            scene_tree = loads(request.form.get('scene_tree'))
            print scene_tree
            instance.load_scene_tree(scene_tree)

    def allowed(self, op, user, instance=None):
        if user:
            if op==ResourceHandler.VIEW or op==ResourceHandler.NEW:
                return True
            else:
                gms = GroupMember.select().where(GroupMember.group == instance.group, GroupMember.member == user, GroupMember.status == GROUP_MASTER)
                return (gms.count() == 1) # user is master in group and can edit
        return False

campaignhandler = CampaignHandler(
        Campaign,
        model_form(Campaign, exclude=['slug']),
        'campaign/campaign_page.html',
        'campaign.campaign_detail')

class SceneHandler(ResourceHandler):
    def allowed(self, op, user, instance=None):
        if user:
            if op==ResourceHandler.VIEW or op==ResourceHandler.NEW:
                return True
            else:
                gms = GroupMember.select().where(GroupMember.group == instance.campaign.group, GroupMember.member == user, GroupMember.status == GROUP_MASTER)
                return (gms.count() == 1) # user is master in group and can edit
        return False

    def get_redirect_url(self, instance):
        return url_for(self.route, slug=instance.slug)

scenehandler = SceneHandler(
    Scene,
    model_form(Scene, exclude=['order', 'parent', 'campaign']),
    'campaign/scene_page.html',
    'campaign.scene_detail')

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
    return scenehandler.handle_request(ResourceHandler.NEW)

@campaign.route('/sessions/<id>', methods=['GET', 'POST'])
@auth.login_required
def session_detail(id):
    return scenehandler.handle_request(ResourceHandler.EDIT, get_object_or_404(Session, Session.id == id))

@campaign.route('/campaigns/')
def campaigns():
    campaigns = Campaign.select()
    return render_template('campaign/campaigns.html', campaigns=campaigns)

@auth.login_required
@campaign.route('/campaigns/new', methods=['GET', 'POST'] )
def campaign_new():
    return campaignhandler.handle_request(ResourceHandler.NEW)

@campaign.route('/campaigns/<slug>', methods=['GET', 'POST'] )
def campaign_detail(slug):
    return campaignhandler.handle_request(ResourceHandler.EDIT, get_object_or_404(Campaign, Campaign.slug == slug))

@auth.login_required
@campaign.route('/campaigns/<slug>/scenes/new', methods=['GET', 'POST'] )
def scene_new(slug):
    return campaignhandler.handle_request(ResourceHandler.NEW)

@campaign.route('/campaigns/<slug>/scenes/<id>', methods=['GET', 'POST'] )
def scene_detail(slug, id):
    return campaignhandler.handle_request(ResourceHandler.EDIT, get_object_or_404(Scene, Scene.id == id))

@auth.login_required
@campaign.route('/campaigns/<slug>/scenes/<id>/delete', methods=['GET', 'POST'] )
def scene_delete(slug, id):
    return scenehandler.handle_request(ResourceHandler.DELETE, get_object_or_404(Scene, Scene.id == id))

