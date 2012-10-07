from flask_peewee.utils import object_list, get_object_or_404
from flask import abort, request, g, redirect, url_for, render_template, flash, Blueprint
from auth import auth
from api import api_json
from app import error_response, generate_flash
from models import *

def create_tables():
    User.create_table(fail_silently=True)
    Relationship.create_table(fail_silently=True)
    Message.create_table(fail_silently=True)
    Note.create_table(fail_silently=True)
    Group.create_table(fail_silently=True)
    GroupMaster.create_table(fail_silently=True)
    GroupPlayer.create_table(fail_silently=True)

social = Blueprint('social', __name__, template_folder='templates')

@social.route('/')
@auth.login_required
def index():
    user = auth.get_logged_in_user()
    following_messages = Message.select().where( Q(conversation=0) & Q(user__in=user.following()) 
    ).order_by(('pub_date', 'desc'))
    return object_list('social/social.html', following_messages, 'following_message_list')

@social.route('/public/')
def public_timeline():
    messages = Message.select().where(conversation=0).order_by(('pub_date', 'desc'))
    return object_list('social/public_messages.html', messages, 'message_list')

@social.route('/conversations/', methods=['GET'])
@auth.login_required
def conversations():
    user = auth.get_logged_in_user()
    conversations = Conversation.select().join(ConversationMembers).where( member=user)
    return object_list('social/conversations.html', conversations, 'conversation_list')

@social.route('/conversations/new/', methods=['GET', 'POST'])
@auth.login_required
def conversation_new():
    user = auth.get_logged_in_user()
    # We expect ?modal or ?modal=true
    modal = request.args.has_key('modal')
    
    if request.method == 'GET' and request.args.get('recipients'):
        # We expect a comma separated arg, e.g. ?recipients=user1,user2 or
        # ?recipients=user1&recipients=user2
        recipients = []
        for r in request.args.getlist('recipients'):
            recipients.extend([r.strip() for r in r.split(',')])
        print recipients
        r_query = User.select().where(username__in=recipients)
        recipients = [r for r in r_query] # Iterate now to get a list, not a query object
        print "Found recipients %s from request param %s" % (recipients, request.args.getlist('recipients'))
        # Get most recent conversation if there is one
        convs = user.get_conversations_with(recipients).order_by(('modified_date','desc')).paginate(1,1)
        print convs.sql()
        convs = [c for c in convs] # Iterate to fetch actual results
        print convs
        if convs: #not empty
            # Send us on to the actual conversation to continue!
            print url_for('.conversation_detail', conv_id=convs[0].id, modal=modal)
            return redirect(url_for('.conversation_detail', conv_id=convs[0].id, modal=modal))
        else: # No conversation exists, give empty form
            # If true, we will not show recipients chooser, same render setting as when having a conversation
            return render_template('social/conversation_page.html', recipients=recipients, modal=modal, fixed_recipients=request.args.has_key('fixed_recipients'))

    elif request.method == 'POST' and request.form['recipients'] and request.form['content']:
        # We expect one or more values with key recipients, e.g recipients=user1, recipients=user2
        # request.form is a MultiDict, which allows one or many values per key
        # we want to get all values for key recipients, so we use getlist()
        recipients = request.form.getlist('recipients')
        r_query = User.select().where(username__in=request.form.getlist('recipients'))
        recipients = [r for r in r_query] # Iterate now to get a list, not a query object
        print "Found recipients %s from request param %s" % (recipients, request.args.getlist('recipients'))
        # Will try to create a new conversation if none already exists
        conversation = user.get_or_create_conversation_with(recipients)
        message = Message.create(
            user=user,
            content=request.form['content'],
            conversation=conversation
        )
        return redirect(url_for('.conversation_detail', conv_id=conversation.id, modal=modal))
    else:
        abort(400) # No recipients, so who would the conversation be with?
 
        
@social.route('/conversations/<conv_id>/', methods=['GET', 'POST'])
@auth.login_required
def conversation_detail(conv_id):
    user = auth.get_logged_in_user()
    modal = request.args.has_key('modal')
    
    conversation = get_object_or_404(Conversation, id=conv_id)
    messages = Message.select().where(conversation=conv_id).order_by(('pub_date', 'desc'))
    recipients = [r for r in conversation.members()]
    recipients.remove(user) # TODO check for error
    # We are updating a conversation
    if request.method == 'POST' and request.form['content']:
        message = Message.create(
            user=user,
            content=request.form['content'],
            conversation=conversation
        )
        flash('Your message has been created')
        # .conversation_detail means to route to this blueprint (social), method conversation_detail
        return redirect(url_for('.conversation_detail', conv_id=conversation.id, modal=modal))
    return object_list('social/conversation_page.html', messages, 'message_list', conversation=conversation, recipients=recipients, modal=modal)    
    
@social.route('/following/')
@auth.login_required
def following():
    user = auth.get_logged_in_user()
    return object_list('social/user_following.html', user.following(), 'user_list')

@social.route('/followers/')
@auth.login_required
def followers():
    user = auth.get_logged_in_user()
    return object_list('social/user_followers.html', user.followers(), 'user_list')

@social.route('/users/')
def user_list():
    user = auth.get_logged_in_user()
    if user:
        mastered_groups = Group.select().join(GroupMember).where(member=user,status=GROUP_MASTER)
        # For each user in the groups mastered by current user, 
        mastered_members = dict()
        for gm in GroupMember.select().where(group__in=mastered_groups):
            if gm.member.username != user.username: # remove ourselves, no need to check that again!
                mastered_members['%s_%s' % (gm.member.username,gm.group.id)] = gm
    users = User.select().order_by('username')
    return object_list('social/all_users.html', users, 'user_list', mastered_groups=mastered_groups, mastered_members=mastered_members)

@social.route('/groups/')
def groups():
    user = auth.get_logged_in_user() 
    my_master_groups = Group.select().join(GroupMember).where(member=user,status=GROUP_MASTER)
    groups = Group.select().order_by('name')
    return object_list('social/groups.html', groups, 'groups', my_master_groups=my_master_groups)

@social.route('/groups/new', methods=['GET', 'POST'])
@auth.login_required
def group_new():
    return edit_group(request)
        
@social.route('/groups/<groupslug>/delete', methods=['GET', 'POST'])
@auth.login_required
def group_delete(groupslug):
    group = get_object_or_404(Group, slug=groupslug)
    user = auth.get_logged_in_user()
    masters = list(group.masters())
    #print "if not user=%s or not user in masters=%s or len(list(masters))>1=%s" % (not user, not user in masters, len(masters)>1) 
    if not user or not user in masters or len(masters)>1:
        return error_response('You need to be logged in and the only master of this group to delete it')
    if request.method == 'GET':            
        return render_template('includes/change_members.html', \
            url=url_for('social.group_delete',groupslug=groupslug), action='delete', \
            instances={'group':[group.slug]})
    elif request.method == 'POST':
        for gm in group.members():
            gm.delete_instance()
        group.delete_instance()
        return redirect(url_for('social.groups'))

@social.route('/groups/<groupslug>/', methods=['GET', 'POST'])
def group_detail(groupslug):
    group = get_object_or_404(Group, slug=groupslug)
    return edit_group(request, group)
    
def edit_group(request, group=None):
    modal = request.args.has_key('modal')
    user = auth.get_logged_in_user()
    edit_allowed = user and (not group or user in group.masters()) # user exist and is master or the group is new
    if request.method == 'GET':
        form = GroupForm(obj=group) if edit_allowed else None
        return render_template('social/group_page.html', group=group, form=form, modal=modal)
    elif request.method == 'POST': 
        if not edit_allowed:
            return error_response('You need to be logged in and master of this group to edit')
        if matches_form(GroupForm, request.form):
            is_newgroup = not group
            form = GroupForm(request.form, obj=group)
            if form.validate():
                if is_newgroup: # We're creating a new group
                    group = Group()
                form.populate_obj(group)
                group.save()
                if is_newgroup: # Add current user as master for created group
                    group.addMasters([user]) 
                edit_group_members(group, request, add=True, master=False)
                flash('Your changes have been saved')
                return redirect(url_for('.group_detail', groupslug=group.slug))
        return error_response('There were errors with your submission')
        #return redirect(url_for('.group_detail', groupslug=group.slug, modal=modal, partial=True))

@social.route('/groups/<groupslug>/members/<action>', methods=['GET','POST'])
@auth.login_required
def group_members_change(groupslug, action):
    group = get_object_or_404(Group, slug=groupslug)
    user = auth.get_logged_in_user()
    if user not in group.masters():
        return error_response('Logged in user %s is not master of group %s so cannot %s' % (user.username, group.name, action))
    if request.method == 'GET':
        masters = User.select().where(username__in=request.args.getlist('masters')) if request.args.has_key('masters') else None
        players = User.select().where(username__in=request.args.getlist('players')) if request.args.has_key('players') else None
        if not masters and not players:
            return error_response('No players or masters given for %s' % action)
        return render_template('includes/change_members.html', \
            url=url_for('social.group_members_change',groupslug=groupslug, action=action), action=action, \
            instances={'masters':masters, 'players':players})
    else: # POST
        if not request.form.has_key('masters') and not request.form.has_key('players'):
            return error_response('No players or masters given for %s' % action)
        changes, resp = edit_group_members(group, request, add=(action=="add"), master=False)
        if resp:
            return resp
        return render_template('social/group_member_view.html', members=changes, group=group, form=True, partial=True)

def edit_group_members(group, r, add, master):
    formdata = r.form
    modal = r.args.has_key('modal')
    changes = []
    if formdata.has_key('masters'):
        masters = list(User.select().where(username__in=formdata.getlist('masters')))
        if not masters:
            return [],error_response('None of the given users %s to %s are recognized' % (formdata.getlist('masters'), 'add' if add else 'remove'))
        masters = group.addMembers(masters, GROUP_MASTER) if add else group.removeMembers(masters)
        generate_flash('Added' if add else 'Removed','master',[gm.member.username for gm in masters])
        changes.extend(masters)
    if formdata.has_key('players'):
        players = list(User.select().where(username__in=formdata.getlist('players')))
        if not players:
            return [],error_response('None of the given users %s to %s are recognized' % (formdata.getlist('players'), 'add' if add else 'remove'))
        players = group.addMembers(players, GROUP_PLAYER) if add else group.removeMembers(players)
        generate_flash('Added' if add else 'Removed','player',[gm.member.username for gm in players])
        changes.extend(players)
    return changes, None

@social.route('/test')
def test():
    flash("Testing testing")
    return render_template('includes/flash.html', base=False)

@social.route('/users/<username>/')
def user_detail(username):
    user = get_object_or_404(User, username=username)
    messages = user.message_set.order_by(('pub_date', 'desc'))
    return object_list('social/user_detail.html', messages, 'message_list', person=user, modal=request.args.has_key('modal'))

@social.route('/users/<username>/follow/', methods=['POST'])
@auth.login_required
def user_follow(username):
    user = get_object_or_404(User, username=username)
    Relationship.get_or_create(
        from_user=auth.get_logged_in_user(),
        to_user=user,
    )
    flash('You are now following %s' % user.username)
    # Note point "." before redirect route, it refers to function in this blueprint (e.g social)
    return redirect(url_for('.user_detail', username=user.username, modal=request.args.has_key('modal')))

@social.route('/users/<username>/unfollow/', methods=['POST'])
@auth.login_required
def user_unfollow(username):
    user = get_object_or_404(User, username=username)
    Relationship.delete().where(
        from_user=auth.get_logged_in_user(),
        to_user=user,
    ).execute()
    flash('You are no longer following %s' % user.username)
    return redirect(url_for('.user_detail', username=user.username, modal=request.args.has_key('modal')))