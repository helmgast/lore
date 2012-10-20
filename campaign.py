from flask import request, redirect, url_for, render_template, Blueprint, flash
from auth import auth
from flask_peewee.utils import get_object_or_404, object_list, slugify
from models import Group, GroupMember, Campaign, CampaignForm, Session, SessionForm, Scene, SceneForm, GROUP_MASTER
from datetime import datetime, timedelta
from app import error_response, generate_flash
from json import loads

campaign = Blueprint('campaign', __name__, template_folder='templates')

@campaign.route('/')
def index():
    return campaigns()

@campaign.route('/sessions/')
@auth.login_required
def sessions():
    user = auth.get_logged_in_user()
    member_in_groups = Group.select().join(GroupMember).where(GroupMember.member == user)
    sessions = Session.select().join(Campaign).where(Campaign.group << member_in_groups)
    form = SessionForm()
    return render_template('campaign/sessions.html', sessions=sessions)

@campaign.route('/sessions/new', methods=['GET', 'POST'])
@auth.login_required
def session_new():
    return edit_session(request)

@campaign.route('/sessions/<id>', methods=['GET', 'POST'])
@auth.login_required
def session_detail(id):
    the_session = get_object_or_404(Session, Session.id == id)
    return edit_session(request, the_session)

def edit_session(request, the_session=None):
    user = auth.get_logged_in_user()
    if the_session:
        group = the_session.campaign.group
        gms = GroupMember.select().where(GroupMember.group == group, GroupMember.member == user)
        edit_allowed = (gms.count() == 1) # visiting user is in group and can edit
    else:
        edit_allowed = True # Because we are creating a new session
    if request.method == 'GET':
        play_start = datetime.now()
        if not the_session and request.args.has_key('play_start'):
            play_start = datetime.strptime(request.args.get('play_start'),'%Y-%m-%d')
            play_start = play_start + timedelta(hours=18) # start at 18 in evening by default
        #play_end = play_start + timedelta(hours=4) # by default, put end 4h after start
        form = SessionForm(obj=the_session, play_start=play_start) if edit_allowed else None
        return render_template('campaign/session_page.html', the_session=the_session, form=form, modal=request.args.has_key('modal'))
    elif request.method == 'POST':
        if not edit_allowed:
            return error_response('You need to be a member of this session\'s group to edit')
        is_new = not the_session
        form = SessionForm(request.form, obj=the_session)
        if form.validate():
            if is_new: # We're creating a new session
                the_session = Session()
            form.populate_obj(the_session)
            the_session.save()
            user.log("created session %s" % the_session)
            flash('Your changes have been saved')
            return redirect(url_for('.session_detail', id=the_session.id))
        return error_response('There were errors with your submission')

@campaign.route('/campaigns/')
def campaigns():
    campaigns = Campaign.select()
    return render_template('campaign/campaigns.html', campaigns=campaigns)

@auth.login_required
@campaign.route('/campaigns/new', methods=['GET', 'POST'] )
def campaign_new():
    return edit_campaign(request)

@campaign.route('/campaigns/<slug>', methods=['GET', 'POST'] )
def campaign_detail(slug):
    campaign = get_object_or_404(Campaign, Campaign.slug == slug)
    return edit_campaign(request, campaign)

def edit_campaign(request, campaign=None):
    user = auth.get_logged_in_user()
    mastered_groups = Group.select().join(GroupMember).where(GroupMember.member == user, GroupMember.status == GROUP_MASTER)
    if campaign:
        edit_allowed = campaign.group in mastered_groups # user is master over this campaign
    else:
        edit_allowed = mastered_groups.count() > 0 # need to be master of something to create a new campaign
    if request.method == 'GET':
        form = None
        if edit_allowed:
            form = CampaignForm(obj=campaign)
            form.group.query = mastered_groups
        scenes = Scene.select().where(Scene.campaign == campaign, Scene.parent >> None).order_by(Scene.order.asc()) # is null
        return render_template('campaign/campaign_page.html', campaign=campaign, scenes=scenes, form=form, sceneform=SceneForm(), modal=request.args.has_key('modal'))
    elif request.method == 'POST':
        if not edit_allowed:
            return error_response('You need to be a member of this session\'s group to edit')
        is_new = not campaign
        form = CampaignForm(request.form, obj=campaign)
        if form.validate():
            if is_new: # We're creating a new session
                campaign = Campaign()
            form.populate_obj(campaign)
            campaign.save()
            if request.form.has_key('scene_tree'):
                scene_tree = loads(request.form.get('scene_tree'))
                print scene_tree
                campaign.load_scene_tree(scene_tree)
            user.log("created campaign %s" % campaign)
            flash('Your changes have been saved')
            return redirect(url_for('.campaign_detail', slug=campaign.slug))
        else:
            print form.errors
        return error_response('There were errors with your submission')

@auth.login_required
@campaign.route('/campaigns/<slug>/scenes/new', methods=['GET', 'POST'] )
def scene_new(slug):
    return edit_scenes(slug)

@campaign.route('/campaigns/<slug>/scenes/<id>', methods=['GET', 'POST'] )
def scene_detail(slug, id):
    scene = get_object_or_404(Scene, Scene.id == id)
    return edit_scenes(slug, scene)

@auth.login_required
@campaign.route('/campaigns/<slug>/scenes/<id>/delete', methods=['GET', 'POST'] )
def scene_delete(slug, id):
    scene = get_object_or_404(Scene, Scene.id == id)

def edit_scenes(slug, scene=None):
    campaign = get_object_or_404(Campaign, Campaign.slug == slug)
    user = auth.get_logged_in_user()
    mastered_groups = Group.select().join(GroupMember).where(GroupMember.member == user, GroupMember.status == GROUP_MASTER)
    edit_allowed = campaign.group in mastered_groups # user is master over this campaign
    if request.method == 'GET':
        form = SceneForm(obj=scene) if edit_allowed else None
        return render_template('campaign/scene_page.html', scene=scene, form=form, modal=request.args.has_key('modal'))
    elif request.method == 'POST':
        if not edit_allowed:
            return error_response('You need to be a master of this campaign to edit scenes')
        is_new = not scene
        form = SceneForm(request.form, obj=scene)
        if form.validate():
            if is_new:
                scene = Scene()
            form.populate_obj(scene)
            scene.save()
            user.log("created scene %s" % scene)
            flash('Your changes have been saved')
            return redirect(url_for('.scene_detail', slug=slug, id=scene.id))
        else:
            print form.errors
    return error_response('There were errors with your submission')


