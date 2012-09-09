# coding=utf-8

from models import *
from generator import *
from world import *
from flask_peewee.utils import make_password

def setup_models():
    User.drop_table(fail_silently=True)
    User.create_table()

    mf = User.create(username='admin', password=make_password('admin'), email='ripperdoc@gmail.com', active=True,
        admin=True, realname='Martin F')
    nf = User.create(username='niklas', password=make_password('niklas'), email='user@user.com', active=True,
        admin=False, realname='Niklas F')
    pf = User.create(username='per', password=make_password('per'), email='user@user.com', active=True, admin=False,
        realname='Per F')
    mb = User.create(username='marco', password=make_password('marco'), email='user@user.com', active=True, admin=False,
        realname='Marco B')
    fj = User.create(username='fredrik', password=make_password('fredrik'), email='user@user.com', active=True,
        admin=False, realname='Fredrik J')
    pd = User.create(username='paul', password=make_password('paul'), email='user@user.com', active=True, admin=False,
        realname='Paul D')
    ar = User.create(username='alex', password=make_password('alex'), email='user@user.com', active=True, admin=False,
        realname='Alex R')
    pn = User.create(username='petter', password=make_password('petter'), email='user@user.com', active=True,
        admin=False, realname='Petter N')
    ks = User.create(username='krister', password=make_password('krister'), email='user@user.com', active=True,
        admin=False, realname='Krister S')
    cs = User.create(username='calle', password=make_password('calle'), email='user@user.com', active=True, admin=False,
        realname='Carl-Johan S')
    mj = User.create(username='mattias', password=make_password('mattias'), email='user@user.com', active=True,
        admin=False, realname='Mattias J')
    rl = User.create(username='robin', password=make_password('robin'), email='user@user.com', active=True, admin=False,
        realname='Robin L')
    rj = User.create(username='rikard', password=make_password('rikard'), email='user@user.com', active=True,
        admin=False, realname='Rikard J')
    vs = User.create(username='victoria', password=make_password('victoria'), email='user@user.com', active=True,
        admin=False, realname='Victoria S')
    je = User.create(username='john', password=make_password('john'), email='user@user.com', active=True, admin=False,
        realname='John E')
    ad = User.create(username='anders', password=make_password('anders'), email='user@user.com', active=True,
        admin=False, realname='Anders D')
    jc = User.create(username='johan', password=make_password('johan'), email='user@user.com', active=True, admin=False,
        realname='Johan C')
    jg = User.create(username='jonathan', password=make_password('jonathan'), email='user@user.com', active=True,
        admin=False, realname='Jonathan G')
    User.create(username='user1', password=make_password('user'), email='user@user.com', active=True, admin=False,
        realname='User Userson')
    User.create(username='user2', password=make_password('user'), email='user@user.com', active=True, admin=False,
        realname='User Userson')
    User.create(username='user3', password=make_password('user'), email='user@user.com', active=True, admin=False,
        realname='User Userson')
    User.create(username='user4', password=make_password('user'), email='user@user.com', active=True, admin=False,
        realname='User Userson')
    
    Article.drop_table(fail_silently=True)
    Article.create_table()
    a = Article(title="Mundana", content=u'Mundana är en värld')
    a.save()
    
    Metadata.drop_table(fail_silently=True)
    Metadata.create_table()
    Metadata.create(article=a, key='test', value='testvalue')
    
    Relationship.drop_table(fail_silently=True)
    Relationship.create_table()
    Relationship.create(from_user=mf, to_user=nf)
    Relationship.create(from_user=nf, to_user=mf)
    Relationship.create(from_user=rj, to_user=vs)
    Relationship.create(from_user=mf, to_user=ks)
    Relationship.create(from_user=jc, to_user=nf)
    Relationship.create(from_user=nf, to_user=jc)
    Relationship.create(from_user=ar, to_user=mf)
    Relationship.create(from_user=mf, to_user=ar)
    Relationship.create(from_user=mf, to_user=mb)
    Relationship.create(from_user=mb, to_user=vs)
    Relationship.create(from_user=ar, to_user=mb)

    Group.drop_table(fail_silently=True)
    Group.create_table()
    ng = Group.create(name='Nero', location='Gothenburg')
    ng.save()
    mg = Group.create(name='Nemesis', location='Gothenburg')
    mg.save()
    kg = Group.create(name='Kulthack', location='Gothenburg')
    kg.save()

    GroupMaster.drop_table(fail_silently=True)
    GroupMaster.create_table()
    GroupMaster.create(group=ng, master=mf)
    GroupMaster.create(group=mg, master=nf)
    GroupMaster.create(group=kg, master=rl)

    GroupPlayer.drop_table(fail_silently=True)
    GroupPlayer.create_table()
    GroupPlayer.create(group=ng, player=nf)
    GroupPlayer.create(group=ng, player=ar)
    GroupPlayer.create(group=ng, player=mb)
    GroupPlayer.create(group=ng, player=pn)
    GroupPlayer.create(group=ng, player=pf)
    GroupPlayer.create(group=ng, player=fj)
    GroupPlayer.create(group=ng, player=pd)

    GroupPlayer.create(group=mg, player=jg)
    GroupPlayer.create(group=mg, player=jc)
    GroupPlayer.create(group=mg, player=pn)

    GroupPlayer.create(group=kg, player=mb)
    GroupPlayer.create(group=kg, player=pn)
    GroupPlayer.create(group=kg, player=ks)
    
    Conversation.drop_table(fail_silently=True)
    Conversation.create_table()
    c1 = Conversation.create()
    c2 = Conversation.create()
    c3 = Conversation.create()
    
    ConversationMembers.drop_table(fail_silently=True)
    ConversationMembers.create_table()
    ConversationMembers.create(conversation=c1, member=mf)
    ConversationMembers.create(conversation=c1, member=nf)
    
    ConversationMembers.create(conversation=c2, member=mf)
    ConversationMembers.create(conversation=c2, member=mb)
    
    ConversationMembers.create(conversation=c3, member=nf)
    ConversationMembers.create(conversation=c3, member=ks)    
    
    # Make sure you use unicode strings by prefixing with u''
    Message.drop_table(fail_silently=True)
    Message.create_table()

    Message.create(user=nf, content=u'Hur går det, får jag höja min xp som vi pratade om?', conversation=c1)
    Message.create(user=jg, content=u'Kul spel sist!')
    Message.create(user=vs, content=u'Min karaktär dog, helvete!')
    Message.create(user=ks, content=u'När får jag vara med då?')
    Message.create(user=ar, content=u'Jag tar med ölen')
    Message.create(user=mf, content=u'Visst, inga problem1', conversation=c1)
    Message.create(user=mf, content=u'Vi borde testa raconteur snart!', conversation=c2)
    Message.create(user=mb, content=u'Definitivt!', conversation=c2)
    Message.create(user=nf, content=u'Hallå?', conversation=c3)
        
    GeneratorRepeatRule.drop_table(fail_silently=True)
    GeneratorRepeatRule.create_table()
    
    StringGenerator.drop_table(fail_silently=True)
    StringGenerator.create_table()
    StringGenerator.create(name="Default Generator")

    Campaign.drop_table(fail_silently=True)
    Campaign.create_table()

    Scene.drop_table(fail_silently=True)
    Scene.create_table()
    
    Session.drop_table(fail_silently=True)
    Session.create_table()
    
    SessionPresentUser.drop_table(fail_silently=True)
    SessionPresentUser.create_table()
