from flask_peewee.utils import object_list, get_object_or_404
from flask import abort, request, redirect, url_for, render_template, flash, Blueprint
from auth import auth
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

@social.route('/conversation/', methods=['GET'])
@auth.login_required
def conversation():
    user = auth.get_logged_in_user()
    conversations = Conversation.select().join(ConversationMembers).where( member=user)
    return object_list('social/conversation.html', conversations, 'conversation_list')

@social.route('/conversation/new/', methods=['GET', 'POST'])
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
            return render_template('social/conversation_detail.html', recipients=recipients, modal=modal, fixed_recipients=request.args.has_key('fixed_recipients'))

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
 
        
@social.route('/conversation/<conv_id>/', methods=['GET', 'POST'])
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
    return object_list('social/conversation_detail.html', messages, 'message_list', conversation=conversation, recipients=recipients, modal=modal)    
    
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
        mastered_groups = user.master_in_groups()
        # For faster use in template, create dict for each username and which
        # group they belong to (as master or as player)
        for g in mastered_groups:
            group_masters = {}
            group_players = {}
            for u in g.masters():
                # Set to True to mark they are masters
                if u.username in group_masters:
                    group_masters[u.username].append(g.id)
                else:
                    group_masters[u.username] = [g.id]
            for u in g.players():
                # Set to False to mark they are not masters
                if u.username in group_players:
                    group_players[u.username].append(g.id)
                else:
                    group_players[u.username] = [g.id]
        del group_masters[user.username] # remove ourselves, no need to check that again!
    users = User.select().order_by('username')
    
    return object_list('social/all_users.html', users, 'user_list', mastered_groups=mastered_groups, group_masters=group_masters, group_players=group_players)

@social.route('/groups/')
def groups():
    user = auth.get_logged_in_user() 
    my_master_groups = user.master_in_groups()
    groups = Group.select().order_by('name')
    return object_list('social/groups.html', groups, 'groups', my_master_groups=my_master_groups)

@social.route('/groups/new', methods=['GET', 'POST'])
@auth.login_required
def group_new():
    user = auth.get_logged_in_user()
    # We expect ?modal or ?modal=true
    modal = request.args.has_key('modal')
    if request.method == 'GET':
        form = GroupForm()
        return render_template('social/group_detail.html', form=form)        
        # We expect a comma separated arg, e.g. ?recipients=user1,
    elif request.method == 'POST':
        # This POST sets attributes of the normal GroupForm direct fields
        form = GroupForm(request.form)
        if form.validate():
            group = Group.create()
            form.populate_obj(group)
            group.save()
            flash('Your changes have been saved')
            return redirect(url_for('.group_detail', groupslug=group.slug))
        else:
            flash('There were errors with your submission')
            return redirect(url_for('.group_detail', groupslug=group.slug))
    else:
        abort(400) # No members in url or form params
        
@social.route('/groups/<groupslug>/', methods=['GET', 'POST'])
def group_detail(groupslug):
    group = get_object_or_404(Group, slug=groupslug)
    modal = request.args.has_key('modal')
    if request.method == 'GET':
        form = GroupForm(obj=group)
        print "Rendering modal? %s" % modal
        return render_template('social/group_detail.html', group=group, form=form, modal=modal)
    elif request.method == 'POST': 
        if matches_form(GroupForm, request.form):
            # This POST sets attributes of the normal GroupForm direct fields
            form = GroupForm(request.form, obj=group)
            if form.validate():
                form.populate_obj(group)
                group.save()
                flash('Your changes have been saved')
                return redirect(url_for('.group_detail', groupslug=group.slug))
        flash('There were errors with your submission')
        return redirect(url_for('.group_detail', groupslug=group.slug, modal=modal))              

@social.route('/groups/<groupslug>/addmasters', methods=['POST'])
@auth.login_required
def group_addmasters(groupslug):
    return change_group_members(groupslug, request, add=True, master=True)

@social.route('/groups/<groupslug>/removemasters', methods=['POST'])
@auth.login_required
def group_removemasters(groupslug):
    return change_group_members(groupslug, request, add=False, master=True)
        
@social.route('/groups/<groupslug>/addplayers', methods=['POST'])
@auth.login_required
def group_addplayers(groupslug):
    return change_group_members(groupslug, request, add=True, master=False)
        
@social.route('/groups/<groupslug>/removeplayers', methods=['POST'])
@auth.login_required
def group_removeplayers(groupslug):
    return change_group_members(groupslug, request, add=False, master=False)

def change_group_members(groupslug, r, add, master):
    formdata = r.form
    modal = r.args.has_key('modal')
    if master and formdata.has_key('masters'):
        group = get_object_or_404(Group, slug=groupslug)
        masters = list(User.select().where(username__in=formdata.getlist('masters')))
        if not masters:
            abort(400)
        elif add:
            flash('Added master(s) %s' % [u.username for u in group.addMasters(masters)], 'success')
        else:
            flash('Removed master(s) %s' % [u.username for u in group.removeMasters(masters)], 'success')
        return redirect(url_for('.group_detail', groupslug=group.slug, modal=modal))
    elif not master and formdata.has_key('players'):
        group = get_object_or_404(Group, slug=groupslug)
        players = list(User.select().where(username__in=formdata.getlist('players')))
        if not players:
            abort(400)
        elif add:
            flash('Added player(s) %s' % [u.username for u in group.addPlayers(players)], 'success')
        else:
            flash('Removed player(s) %s' % [u.username for u in group.removePlayers(players)], 'success')
        return redirect(url_for('.group_detail', groupslug=group.slug, modal=modal))                
    else:
        flash('There were errors with your submission')
        return redirect(url_for('.group_detail', groupslug=group.slug, modal=modal)) 
                
@social.route('/users/<username>/')
def user_detail(username):
    user = get_object_or_404(User, username=username)
    messages = user.message_set.order_by(('pub_date', 'desc'))
    print messages
    return object_list('social/user_detail.html', messages, 'message_list', person=user)

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
    return redirect(url_for('.user_detail', username=user.username))

@social.route('/users/<username>/unfollow/', methods=['POST'])
@auth.login_required
def user_unfollow(username):
    user = get_object_or_404(User, username=username)
    Relationship.delete().where(
        from_user=auth.get_logged_in_user(),
        to_user=user,
    ).execute()
    flash('You are no longer following %s' % user.username)
    return redirect(url_for('.user_detail', username=user.username))