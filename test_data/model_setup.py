# coding=utf-8

from model.campaign import *
from model.misc import *
from model.user import *
from model.world import *

from auth import make_password

def altor_date(year, month, day):
    return year*360+(month-1)*30+(day-1)

def setup_models():
    add_test_data()
    
    
def add_test_data():

    # World.drop_collection()
    mundana = World(title="Mundana", publisher="Neogames", description=u"En fantasyvärld för grisodling").save()
    altor = World(title="Altor", publisher=u"Niklas Fröjd", description=u"Drakar Demoner advanced").save()
    kult = World(title="Kult", publisher=u"Äventyrsspel", description=u"Demiurger och nefariter").save()

    # RelationType.drop_collection()
    RelationType(name="child of").save()
    RelationType(name="parent of").save()
    RelationType(name="friend of").save()
    RelationType(name="enemy of").save()
    RelationType(name="distant relative of").save()

    # User.drop_collection()
    mf = User(username='admin', password=make_password('admin'), email='ripperdoc@gmail.com', active=True,
        admin=True, realname='Martin F', description='Always games in a hat. Has a cat.').save()
    nf = User(username='niklas', password=make_password('niklas'), email='user@user.com', active=True,
        admin=False, realname='Niklas F').save()
    pf = User(username='per', password=make_password('per'), email='user@user.com', active=True, admin=False,
        realname='Per F').save()
    mb = User(username='marco', password=make_password('marco'), email='user@user.com', active=True, admin=False,
        realname='Marco B').save()
    fj = User(username='fredrik', password=make_password('fredrik'), email='user@user.com', active=True,
        admin=False, realname='Fredrik J').save()
    pd = User(username='paul', password=make_password('paul'), email='user@user.com', active=True, admin=False,
        realname='Paul D').save()
    ar = User(username='alex', password=make_password('alex'), email='user@user.com', active=True, admin=False,
        realname='Alex R').save()
    pn = User(username='petter', password=make_password('petter'), email='user@user.com', active=True,
        admin=False, realname='Petter N').save()
    ks = User(username='krister', password=make_password('krister'), email='user@user.com', active=True,
        admin=False, realname='Krister S').save()
    User(username='calle', password=make_password('calle'), email='user@user.com', active=True, admin=False,
        realname='Carl-Johan S').save()
    mj = User(username='mattias', password=make_password('mattias'), email='user@user.com', active=True,
        admin=False, realname='Mattias J').save()
    rl = User(username='robin', password=make_password('robin'), email='user@user.com', active=True, admin=False,
        realname='Robin L').save()
    rj = User(username='rikard', password=make_password('rikard'), email='user@user.com', active=True,
        admin=False, realname='Rikard J').save()
    vs = User(username='victoria', password=make_password('victoria'), email='user@user.com', active=True,
        admin=False, realname='Victoria S').save()
    User(username='john', password=make_password('john'), email='user@user.com', active=True, admin=False,
        realname='John E').save()
    User(username='anders', password=make_password('anders'), email='user@user.com', active=True,
        admin=False, realname='Anders D').save()
    jc = User(username='johan', password=make_password('johan'), email='user@user.com', active=True, admin=False,
        realname='Johan C').save()
    cm = User(username='claes', password=make_password('claes'), email='user@user.com', active=True, admin=False,
        realname='Claes M').save()
    dm = User(username='daniel', password=make_password('daniel'), email='user@user.com', active=True, admin=False,
        realname='Daniel M').save()
    jg = User(username='jonathan', password=make_password('jonathan'), email='user@user.com', active=True,
        admin=False, realname='Jonathan G').save()
    User(username='user1', password=make_password('user'), email='user@user.com', active=True, admin=False,
        realname='User Userson').save()
    User(username='user2', password=make_password('user'), email='user@user.com', active=True, admin=False,
        realname='User Userson').save()
    User(username='user3', password=make_password('user'), email='user@user.com', active=True, admin=False,
        realname='User Userson').save()
    User(username='user4', password=make_password('user'), email='user@user.com', active=True, admin=False,
        realname='User Userson').save()
    
    # Article.drop_collection()

    Article(type=ARTICLE_IMAGE,
        title=u"Ljusbringaren bild",
        content=u"No content",
        world=altor,
        creator=mj,
        imagearticle=ImageArticle.create_from_url(
            "http://kaigon.se/wiki/images/6/6b/Ljusets_son.jpg")
            ).save()
    Article(type=ARTICLE_PERSON,
        title=u"Ljusbringaren",
        content=u"No content",
        world=altor,
        creator=rl,
        personarticle = PersonArticle(
            born=altor_date(1653,3,4),
            died=altor_date(1891,12,3),
            gender=GENDER_MALE,
            occupation=u"Ljusbringaren")
        ).save()
    mf.following = [nf, ks, ar, mb]
    mf.save()

#     Relationship(from_user=mf, to_user=nf).save()
#     Relationship(from_user=nf, to_user=mf).save()
#     Relationship(from_user=rj, to_user=vs).save()
#     Relationship(from_user=mf, to_user=ks).save()
# 
#     Relationship(from_user=jc, to_user=nf).save()
#     Relationship(from_user=nf, to_user=jc).save()
#     Relationship(from_user=pf, to_user=nf).save()
#     Relationship(from_user=nf, to_user=pf).save()
#     Relationship(from_user=cm, to_user=nf).save()
#     Relationship(from_user=nf, to_user=cm).save()
#     Relationship(from_user=dm, to_user=nf).save()
#     Relationship(from_user=nf, to_user=dm).save()
#     Relationship(from_user=pf, to_user=jc).save()
#     Relationship(from_user=jc, to_user=pf).save()
#     Relationship(from_user=cm, to_user=jc).save()
#     Relationship(from_user=jc, to_user=cm).save()
#     Relationship(from_user=dm, to_user=jc).save()
#     Relationship(from_user=jc, to_user=dm).save()
#     Relationship(from_user=cm, to_user=pf).save()
#     Relationship(from_user=pf, to_user=cm).save()
#     Relationship(from_user=dm, to_user=pf).save()
#     Relationship(from_user=pf, to_user=dm).save()
#     Relationship(from_user=dm, to_user=cm).save()
#     Relationship(from_user=cm, to_user=dm).save()
# 
#     Relationship(from_user=ar, to_user=mf).save()
#     Relationship(from_user=mf, to_user=ar).save()
#     Relationship(from_user=mf, to_user=mb).save()
#     Relationship(from_user=mb, to_user=vs).save()
#     Relationship(from_user=ar, to_user=mb).save()

    # Conversation.drop_collection()
    c1 = Conversation(members=[mf, nf]).save()
    c2 = Conversation(members=[mf, mb]).save()
    c3 = Conversation(members=[nf, ks]).save()
    
    # Group.drop_collection()
    ng = Group(name='Nero', location='Gothenburg', description=u'Liten spelgrupp som gillar pervers humor').save()
    ng.add_masters([mf])
    ng.add_members([nf, mb, fj, pd, pf, pn])
    ng.save()
    mg = Group(name='Nemesis', location='Gothenburg', description=u'Test').save()
    mg.add_masters([nf])
    mg.add_members([jg,pn,jc,pf,cm,dm])
    mg.save()
    kg = Group(name='Kulthack', location='Gothenburg', description=u'Test').save()
    kg.add_masters([rl])
    kg.add_members([mb, pn, ks])
    kg.save()
    
    # Message.drop_collection()
    # Make sure you use unicode strings by prefixing with u''
    Message(user=nf, content=u'Hur går det, får jag höja min xp som vi pratade om?', conversation=c1).save()
    Message(user=jg, content=u'Kul spel sist!').save()
    Message(user=vs, content=u'Min karaktär dog, helvete!').save()
    Message(user=ks, content=u'När får jag vara med då?').save()
    Message(user=ar, content=u'Jag tar med ölen').save()
    Message(user=mf, content=u'Visst, inga problem1', conversation=c1).save()
    Message(user=mf, content=u'Vi borde testa raconteur snart!', conversation=c2).save()
    Message(user=mb, content=u'Definitivt!', conversation=c2).save()
    Message(user=nf, content=u'Hallå?', conversation=c3).save()

    scmpa = Article(type=ARTICLE_CAMPAIGN, title=u"Spelveckan", world=mundana, content=u"Deep drama at the beginning of July each year.").save()
    cd4ka = Article(type=ARTICLE_CAMPAIGN, title=u"Den Fjärde Konfluxen", world=altor, description=u"Rollpersonerna (Kandor, Zebbe, Navi, Josay och Titziana) är ordensmedlemmar i Yvainorden i staden Yavaris i Banborstland på Pandaros. Yvain är en av de fyra plågade hjältarna och hans ordnar kontrollerar mer eller mindre de civiliserade delarna av kontinenten.").save()
    cd6ka = Article(type=ARTICLE_CAMPAIGN, title=u"Den Sjätte Konfluxen", world=altor, description=u"Kampanjen handlar om professor Joseph Tiesen och hans expedition som sägs ha sänts ut av Kublai Shakkar, kejsare och arkon över Mergal. Expeditionen kommer att resa runt i både Jargal och Pandaros i jakt på allt som kan vara relevant för den kommande sjätte konfluxen.").save()
    kcmpa = Article(type=ARTICLE_CAMPAIGN, title=u"Kult AW", world=kult, description=u"Drama in victorian England at the edge of reality").save()
    ycmpa = Article(type=ARTICLE_CAMPAIGN, title=u"Yerlog", world=mundana, description=u"Time to take over the world!").save()
    
    scmpa.children = [Episode(id=u"1", title=u"Intro"),
                      Episode(id=u"2", title=u"The old man in the taverna"),
                      Episode(id=u"3", title=u"Going to the cave"),
                      Episode(id=u"4", title=u"Not finding the way"),
                      Episode(id=u"5", title=u"The general comes all over")]
    scmpa.save()

    # CampaignInstance.drop_collection()

    scmp = CampaignInstance(campaign=scmpa, name=u"Spelveckan", group=ng, rule_system=u"Eon").save()
    cd4k = CampaignInstance(campaign=cd4ka, name=u"Den Fjärde Konfluxen", group=mg, rule_system=u"Drakar & Demoner").save()
    cd6k = CampaignInstance(campaign=cd6ka, name=u"Den Sjätte Konfluxen", group=mg, rule_system=u"Fate").save()
    kcmp = CampaignInstance(campaign=kcmpa, name=u"Kult AW", group=kg, rule_system=u"AW").save()
    CampaignInstance(campaign=ycmpa, name=u"Yerlog", group=ng, rule_system=u"Eon").save()

    scmp.sessions = [Session(play_start=datetime.datetime(2012,10,20,18,0), play_end=datetime.datetime(2012,10,20,23,0), location=u'Snöflingeg')]
    scmp.save()

    kcmp.sessions = [Session(play_start=datetime.datetime(2012,10,30,18,0), play_end=datetime.datetime(2012,10,30,23,0), location=u'Åby')]
    kcmp.save()

    cd4k.sessions = [Session(play_start=datetime.datetime(2006,07,28,18,0), play_end=datetime.datetime(2006,07,28,23,0), location=u'Snöflingegatan'),
                     Session(play_start=datetime.datetime(2006,07,29,18,0), play_end=datetime.datetime(2006,07,29,23,0), location=u'Snöflingegatan'),
                     Session(play_start=datetime.datetime(2006,07,30,18,0), play_end=datetime.datetime(2006,07,30,23,0), location=u'Snöflingegatan'),
                     Session(play_start=datetime.datetime(2006,12,28,18,0), play_end=datetime.datetime(2006,12,28,23,0), location=u'Mor märtas väg'),
                     Session(play_start=datetime.datetime(2006,12,29,18,0), play_end=datetime.datetime(2006,12,29,23,0), location=u'Mor märtas väg'),
                     Session(play_start=datetime.datetime(2006,12,30,18,0), play_end=datetime.datetime(2006,12,30,23,0), location=u'Persmässvägen'),
                     Session(play_start=datetime.datetime(2007,01,02,18,0), play_end=datetime.datetime(2007,01,02,23,0), location=u'Mjödvägen'),
                     Session(play_start=datetime.datetime(2007,01,03,18,0), play_end=datetime.datetime(2007,01,03,23,0), location=u'Mjödvägen'),
                     Session(play_start=datetime.datetime(2007,01,04,18,0), play_end=datetime.datetime(2007,01,04,23,0), location=u'Storsvängen'),
                     Session(play_start=datetime.datetime(2007,01,05,18,0), play_end=datetime.datetime(2007,01,05,23,0), location=u'Storsvängen')]
    cd4k.save()

    cd6k.sessions = [Session(play_start=datetime.datetime(2009,01,05,18,0), play_end=datetime.datetime(2009,01,05,23,0), location=u'Ulvsbygatan'),
                     Session(play_start=datetime.datetime(2009,01,06,18,0), play_end=datetime.datetime(2009,01,06,23,0), location=u'Ulvsbygatan'),
                     Session(play_start=datetime.datetime(2009,8,9,18,0), play_end=datetime.datetime(2009,8,9,23,0), location=u'Olsäter'),
                     Session(play_start=datetime.datetime(2009,8,10,18,0), play_end=datetime.datetime(2009,8,10,23,0), location=u'Olsäter'),
                     Session(play_start=datetime.datetime(2009,8,11,18,0), play_end=datetime.datetime(2009,8,11,23,0), location=u'Olsäter'),
                     Session(play_start=datetime.datetime(2009,8,12,18,0), play_end=datetime.datetime(2009,8,12,23,0), location=u'Olsäter'),
                     Session(play_start=datetime.datetime(2010,4,19,18,0), play_end=datetime.datetime(2010,4,19,23,0), location=u'Ulvsbygatan'),
                     Session(play_start=datetime.datetime(2010,4,20,18,0), play_end=datetime.datetime(2010,4,20,23,0), location=u'Ulvsbygatan'),
                     Session(play_start=datetime.datetime(2010,4,21,18,0), play_end=datetime.datetime(2010,4,21,23,0), location=u'Ulvsbygatan'),
                     Session(play_start=datetime.datetime(2010,9,3,18,0), play_end=datetime.datetime(2010,9,3,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2010,9,4,18,0), play_end=datetime.datetime(2010,9,4,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2010,9,5,18,0), play_end=datetime.datetime(2010,9,5,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2011,5,27,18,0), play_end=datetime.datetime(2011,5,27,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2011,5,28,18,0), play_end=datetime.datetime(2011,5,28,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2011,5,29,18,0), play_end=datetime.datetime(2011,5,29,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2011,8,20,18,0), play_end=datetime.datetime(201,8,20,23,0), location=u'Olsäter'),
                     Session(play_start=datetime.datetime(2011,8,21,18,0), play_end=datetime.datetime(201,8,21,23,0), location=u'Olsäter'),
                     Session(play_start=datetime.datetime(2011,8,22,18,0), play_end=datetime.datetime(201,8,22,23,0), location=u'Olsäter'),
                     Session(play_start=datetime.datetime(2011,8,24,18,0), play_end=datetime.datetime(201,8,24,23,0), location=u'Olsäter'),
                     Session(play_start=datetime.datetime(2012,1,27,18,0), play_end=datetime.datetime(2012,1,27,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2012,1,28,18,0), play_end=datetime.datetime(2012,1,28,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2012,1,29,18,0), play_end=datetime.datetime(2012,1,29,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2012,4,28,18,0), play_end=datetime.datetime(2012,4,28,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2012,4,29,18,0), play_end=datetime.datetime(2012,4,29,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2012,8,31,18,0), play_end=datetime.datetime(2012,8,31,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2012,9,1,18,0), play_end=datetime.datetime(2012,9,1,23,0), location=u'Mölndalsvägen'),
                     Session(play_start=datetime.datetime(2012,9,2,18,0), play_end=datetime.datetime(2012,9,2,23,0), location=u'Mölndalsvägen')] 
    cd6k.save()
    
    # gil1 = GeneratorInputList(name=u'Korhiv start letter').save()
    # gil2 = GeneratorInputList(name=u'Korhiv middle syllables').save()
    # gil3 = GeneratorInputList(name=u'Korhiv end syllables').save()
    
    # GeneratorInputItem(input_list=gil1, content=u'b').save()
    # GeneratorInputItem(input_list=gil1, content=u'ch').save()
    # GeneratorInputItem(input_list=gil1, content=u'd').save()
    # GeneratorInputItem(input_list=gil1, content=u'f').save()
    # GeneratorInputItem(input_list=gil1, content=u'g').save()
    # GeneratorInputItem(input_list=gil1, content=u'h').save()
    # GeneratorInputItem(input_list=gil1, content=u'j\'').save()
    # GeneratorInputItem(input_list=gil1, content=u'k\'').save()
    # GeneratorInputItem(input_list=gil1, content=u'm').save()
    # GeneratorInputItem(input_list=gil1, content=u'n').save()
    # GeneratorInputItem(input_list=gil1, content=u'r').save()
    # GeneratorInputItem(input_list=gil1, content=u'sh').save()
    # GeneratorInputItem(input_list=gil1, content=u't').save()
    # GeneratorInputItem(input_list=gil1, content=u'v').save()
    # GeneratorInputItem(input_list=gil1, content=u'y').save()
    # GeneratorInputItem(input_list=gil1, content=u'z').save()

    # GeneratorInputItem(input_list=gil2, content=u'ab').save()
    # GeneratorInputItem(input_list=gil2, content=u'ach').save()
    # GeneratorInputItem(input_list=gil2, content=u'ad').save()
    # GeneratorInputItem(input_list=gil2, content=u'af').save()
    # GeneratorInputItem(input_list=gil2, content=u'ag').save()
    # GeneratorInputItem(input_list=gil2, content=u'ah').save()
    # GeneratorInputItem(input_list=gil2, content=u'al\'').save()
    # GeneratorInputItem(input_list=gil2, content=u'am').save()
    # GeneratorInputItem(input_list=gil2, content=u'an').save()
    # GeneratorInputItem(input_list=gil2, content=u'aq').save()
    # GeneratorInputItem(input_list=gil2, content=u'ar').save()
    # GeneratorInputItem(input_list=gil2, content=u'ash').save()
    # GeneratorInputItem(input_list=gil2, content=u'at').save()
    # GeneratorInputItem(input_list=gil2, content=u'av').save()
    # GeneratorInputItem(input_list=gil2, content=u'ay').save()
    # GeneratorInputItem(input_list=gil2, content=u'az').save()
    # GeneratorInputItem(input_list=gil2, content=u'eb').save()
    # GeneratorInputItem(input_list=gil2, content=u'ech').save()
    # GeneratorInputItem(input_list=gil2, content=u'ed').save()
    # GeneratorInputItem(input_list=gil2, content=u'eh').save()
    # GeneratorInputItem(input_list=gil2, content=u'el').save()
    # GeneratorInputItem(input_list=gil2, content=u'em').save()
    # GeneratorInputItem(input_list=gil2, content=u'en').save()
    # GeneratorInputItem(input_list=gil2, content=u'er').save()
    # GeneratorInputItem(input_list=gil2, content=u'esh').save()
    # GeneratorInputItem(input_list=gil2, content=u'ev').save()
    # GeneratorInputItem(input_list=gil2, content=u'ey').save()
    # GeneratorInputItem(input_list=gil2, content=u'ez').save()
    # GeneratorInputItem(input_list=gil2, content=u'ib').save()
    # GeneratorInputItem(input_list=gil2, content=u'ich').save()
    # GeneratorInputItem(input_list=gil2, content=u'id').save()
    # GeneratorInputItem(input_list=gil2, content=u'if').save()
    # GeneratorInputItem(input_list=gil2, content=u'ig').save()
    # GeneratorInputItem(input_list=gil2, content=u'ih').save()
    # GeneratorInputItem(input_list=gil2, content=u'il').save()
    # GeneratorInputItem(input_list=gil2, content=u'im').save()
    # GeneratorInputItem(input_list=gil2, content=u'in').save()
    # GeneratorInputItem(input_list=gil2, content=u'iq').save()
    # GeneratorInputItem(input_list=gil2, content=u'ir\'').save()
    # GeneratorInputItem(input_list=gil2, content=u'ish').save()
    # GeneratorInputItem(input_list=gil2, content=u'iv').save()
    # GeneratorInputItem(input_list=gil2, content=u'iy').save()
    # GeneratorInputItem(input_list=gil2, content=u'iz').save()
    # GeneratorInputItem(input_list=gil2, content=u'od').save()
    # GeneratorInputItem(input_list=gil2, content=u'or\'').save()
    # GeneratorInputItem(input_list=gil2, content=u'oz').save()
    # GeneratorInputItem(input_list=gil2, content=u'um').save()
    # GeneratorInputItem(input_list=gil2, content=u'ûn').save()

    # GeneratorInputItem(input_list=gil3, content=u'ab').save()
    # GeneratorInputItem(input_list=gil3, content=u'ach').save()
    # GeneratorInputItem(input_list=gil3, content=u'ad').save()
    # GeneratorInputItem(input_list=gil3, content=u'af').save()
    # GeneratorInputItem(input_list=gil3, content=u'ag').save()
    # GeneratorInputItem(input_list=gil3, content=u'ah').save()
    # GeneratorInputItem(input_list=gil3, content=u'al').save()
    # GeneratorInputItem(input_list=gil3, content=u'am').save()
    # GeneratorInputItem(input_list=gil3, content=u'ân').save()
    # GeneratorInputItem(input_list=gil3, content=u'aq').save()
    # GeneratorInputItem(input_list=gil3, content=u'ar').save()
    # GeneratorInputItem(input_list=gil3, content=u'ash').save()
    # GeneratorInputItem(input_list=gil3, content=u'at').save()
    # GeneratorInputItem(input_list=gil3, content=u'av').save()
    # GeneratorInputItem(input_list=gil3, content=u'ay').save()
    # GeneratorInputItem(input_list=gil3, content=u'az').save()
    # GeneratorInputItem(input_list=gil3, content=u'êb').save()
    # GeneratorInputItem(input_list=gil3, content=u'ech').save()
    # GeneratorInputItem(input_list=gil3, content=u'êd').save()
    # GeneratorInputItem(input_list=gil3, content=u'eh').save()
    # GeneratorInputItem(input_list=gil3, content=u'el').save()
    # GeneratorInputItem(input_list=gil3, content=u'em').save()
    # GeneratorInputItem(input_list=gil3, content=u'en').save()
    # GeneratorInputItem(input_list=gil3, content=u'er').save()
    # GeneratorInputItem(input_list=gil3, content=u'esh').save()
    # GeneratorInputItem(input_list=gil3, content=u'ev').save()
    # GeneratorInputItem(input_list=gil3, content=u'ey').save()
    # GeneratorInputItem(input_list=gil3, content=u'ez').save()
    # GeneratorInputItem(input_list=gil3, content=u'îb').save()
    # GeneratorInputItem(input_list=gil3, content=u'ich').save()
    # GeneratorInputItem(input_list=gil3, content=u'îd').save()
    # GeneratorInputItem(input_list=gil3, content=u'if').save()
    # GeneratorInputItem(input_list=gil3, content=u'ig').save()
    # GeneratorInputItem(input_list=gil3, content=u'ih').save()
    # GeneratorInputItem(input_list=gil3, content=u'il').save()
    # GeneratorInputItem(input_list=gil3, content=u'im').save()
    # GeneratorInputItem(input_list=gil3, content=u'în').save()
    # GeneratorInputItem(input_list=gil3, content=u'iq').save()
    # GeneratorInputItem(input_list=gil3, content=u'ir').save()
    # GeneratorInputItem(input_list=gil3, content=u'ish').save()
    # GeneratorInputItem(input_list=gil3, content=u'iv').save()
    # GeneratorInputItem(input_list=gil3, content=u'iy').save()
    # GeneratorInputItem(input_list=gil3, content=u'iz').save()
    # GeneratorInputItem(input_list=gil3, content=u'od').save()
    # GeneratorInputItem(input_list=gil3, content=u'or').save()
    # GeneratorInputItem(input_list=gil3, content=u'oz').save()
    # GeneratorInputItem(input_list=gil3, content=u'um').save()
    # GeneratorInputItem(input_list=gil3, content=u'ûn').save()
