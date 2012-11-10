from flask_peewee.utils import object_list, get_object_or_404
from flask import abort, request, redirect, url_for, render_template, flash, Blueprint
from auth import auth
from resource import ResourceHandler
from models import *

social = Blueprint('social', __name__, template_folder='templates')

class GroupHandler(ResourceHandler):
    model_class = Group
    form_class = model_form(model_class, exclude=['slug', 'conversation'])

    def allowed(self, op, user, instance=None):
        if user:
            if op=='view' or op=='new':
                return True
            else:
                return user in instance.masters() # user need to be a master to edit
        return False

@social.route('/')
@auth.login_required
def index():
    user = auth.get_logged_in_user()
    following_messages = Message.select().where(Message.conversation ==0, Message.user << user.following()).order_by(Message.pub_date.desc())
    return object_list('social/social.html', following_messages, 'following_message_list')

@social.route('/public/')
def public_timeline():
    messages = Message.select().where(Message.conversation == 0).order_by(Message.pub_date.desc())
    return object_list('social/public_messages.html', messages, 'message_list')

@social.route('/conversations/', methods=['GET'])
@auth.login_required
def conversations():
    user = auth.get_logged_in_user()
    conversations = Conversation.select().join(ConversationMembers).where( ConversationMembers.member == user)
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
        r_query = User.select().where(User.username << recipients) # In recipients
        recipients = [r for r in r_query] # Iterate now to get a list, not a query object
        print "Found recipients %s from request param %s" % (recipients, request.args.getlist('recipients'))
        # Get most recent conversation if there is one
        convs = list(user.get_most_recent_conversation_with(recipients))
        print convs
        if convs: #not empty
            print "Conversation: %s, id %s and date %s" % (convs[0], str(convs[0].id), str(convs[0].modified_date))
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
        r_query = User.select().where(User.username << request.form.getlist('recipients'))
        recipients = [r for r in r_query] # Iterate now to get a list, not a query object
        print "Found recipients %s from request param %s" % (recipients, request.args.getlist('recipients'))
        # Will try to create a new conversation if none already exists
        # Get most recent conversation if there is one
        convs = list(user.get_most_recent_conversation_with(recipients))
        if convs:
            conversation = convs[0]
        else:
            conversation = Conversation.create()
            conversation.add_members([user]+recipients) # merge lists
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
    
    conversation = get_object_or_404(Conversation, Conversation.id==conv_id)
    messages = Message.select().where(Message.conversation == conv_id).order_by(Message.pub_date.desc())
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

@social.route('/groups/')
def groups():
    user = auth.get_logged_in_user() 
    my_master_groups = Group.select().join(GroupMember).where(GroupMember.member == user, GroupMember.status == GROUP_MASTER)
    groups = Group.select().order_by(Group.name.asc())
    return object_list('social/groups.html', groups, 'groups', my_master_groups=my_master_groups)

@social.route('/groups/new', methods=['GET', 'POST'])
@auth.login_required
def group_new():
    rh = GroupHandler('social/group_page.html')
    return rh.handle_request('new')
        
@social.route('/groups/<groupslug>/delete', methods=['GET', 'POST'])
@auth.login_required
def group_delete(groupslug):
    group = get_object_or_404(Group, Group.slug == groupslug)
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
    rh = GroupHandler('social/group_page.html', get_object_or_404(Group, Group.slug == groupslug))
    return rh.handle_request('edit')
    
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
                    user.log("created group %s" % group.slug)
                edit_group_members(user, group, request, add=True, master=False)
                flash('Your changes have been saved')
                return redirect(url_for('.group_detail', groupslug=group.slug))
        return error_response('There were errors with your submission')
        #return redirect(url_for('.group_detail', groupslug=group.slug, modal=modal, partial=True))

@social.route('/groups/<groupslug>/members/<action>', methods=['GET','POST'])
@auth.login_required
def group_members_change(groupslug, action):
    group = get_object_or_404(Group, Group.slug == groupslug)
    user = auth.get_logged_in_user()
    if user not in group.masters():
        return error_response('Logged in user %s is not master of group %s so cannot %s' % (user.username, group.name, action))
    if request.method == 'GET':
        masters = User.select().where(User.username << request.args.getlist('masters')) if request.args.has_key('masters') else None
        players = User.select().where(User.username << request.args.getlist('players')) if request.args.has_key('players') else None
        if not masters and not players:
            return error_response('No players or masters given for %s' % action)
        return render_template('includes/change_members.html', \
            url=url_for('social.group_members_change',groupslug=groupslug, action=action), action=action, \
            instances={'masters':masters, 'players':players})
    else: # POST
        if not request.form.has_key('masters') and not request.form.has_key('players'):
            return error_response('No players or masters given for %s' % action)
        changes, err = edit_group_members(user, group, request, add=(action=="add"), master=False)
        if err: # There was an error
            return err
        if request.args.get('view') == 'm_group_member_selector' and len(changes)==1: #this option only works if there is one member changed
            # Todo, this is a hack. We want to render one person added or removed. The partial template we use normally used in user_list.html
            # and uses a hash list to quickly render. Here we have to reverse engineer it to achieve the desired outcome...
            mastered_members = dict()
            if action=='add': # if we remove we keep it empty to render it as non-added
                mastered_members['%s_%s' % (changes[0].member.username, group.id)] =changes[0] 
            print mastered_members
            return render_template('social/group_member_selector.html', mastered_groups=[group], mastered_members=mastered_members, person=changes[0].member, partial=True)
        elif request.args.get('view') == 'm_group_member_view':
            return render_template('social/group_member_view.html', members=changes, group=group, form=True, partial=True)
        else:
            return error_response('Need to specify which type of view this request comes from')

def edit_group_members(user, group, r, add, master):
    formdata = r.form
    changes = []
    if formdata.has_key('masters'):
        masters = list(User.select().where(User.username << formdata.getlist('masters')))
        if not masters:
            return [],error_response('None of the given users %s to %s are recognized' % (formdata.getlist('masters'), 'add' if add else 'remove'))
        masters = group.addMembers(masters, GROUP_MASTER) if add else group.removeMembers(masters)
        if not masters:
            return [],error_response('None of the given users %s could be %s' % (formdata.getlist('masters'), 'added' if add else 'removed'))
        user.log(generate_flash('Added' if add else 'Removed','master',[gm.member.username for gm in masters],group.slug))
        changes.extend(masters)
    if formdata.has_key('players'):
        players = list(User.select().where(User.username << formdata.getlist('players')))
        if not players:
            return [],error_response('None of the given users %s to %s are recognized' % (formdata.getlist('players'), 'add' if add else 'remove'))
        players = group.addMembers(players, GROUP_PLAYER) if add else group.removeMembers(players)
        if not players:
            return [],error_response('None of the given users %s could be %s' % (formdata.getlist('players'), 'added' if add else 'removed'))
        user.log(generate_flash('Added' if add else 'Removed','player',[gm.member.username for gm in players],group.slug))
        changes.extend(players)
    return changes, None

@social.route('/test')
def test():
    flash("Testing testing")
    return render_template('includes/flash.html', base=False)

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
        mastered_groups = Group.select().join(GroupMember).where(GroupMember.member == user, GroupMember.status == GROUP_MASTER)
        # For each user in the groups mastered by current user, 
        mastered_members = dict()
        for gm in GroupMember.select().where(GroupMember.group << mastered_groups):
            if gm.member.username != user.username: # remove ourselves, no need to check that again!
                mastered_members['%s_%s' % (gm.member.username,gm.group.id)] = gm
    users = User.select().order_by(User.username.asc())
    return object_list('social/all_users.html', users, 'user_list', mastered_groups=mastered_groups, mastered_members=mastered_members)

@social.route('/users/<username>/', methods=['GET','POST'])
def user_detail(username):
    user = get_object_or_404(User, User.username == username)
    ri = ResourceHandler(User, 'social/user_detail.html', user)
    return ri.handle_request('edit')

@social.route('/users/<username>/follow/', methods=['POST'])
@auth.login_required
def user_follow(username):
    user = get_object_or_404(User, User.username == username)
    logged_in = auth.get_logged_in_user()
    Relationship.get_or_create(from_user=logged_in, to_user=user)
    flash('You are now following %s' % user.username)
    logged_in.log('now following %s' % user.username)
    user.log('now being followed by %s' % logged_in.username)
    # Note point "." before redirect route, it refers to function in this blueprint (e.g social)
    return redirect(url_for('.user_detail', username=user.username, modal=request.args.has_key('modal')))

@social.route('/users/<username>/unfollow/', methods=['POST'])
@auth.login_required
def user_unfollow(username):
    user = get_object_or_404(User, User.username == username)
    logged_in = auth.get_logged_in_user()
    Relationship.delete().where(Relationship.from_user==auth.get_logged_in_user(),Relationship.to_user==user).execute()
    flash('You are no longer following %s' % user.username)
    logged_in.log('now not following %s' % user.username)
    user.log('was unfollowed by %s' % logged_in.username)
    return redirect(url_for('.user_detail', username=user.username, modal=request.args.has_key('modal')))