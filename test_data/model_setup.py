# coding=utf-8

from model.campaign import *
from model.misc import *
from model.user import *
from model.world import *
from model.shop import *
import datetime

from auth import make_password

def altor_date(year, month, day):
  return year*360+(month-1)*30+(day-1)

def setup_models():
  add_test_data()
    
def add_test_data():
  # World.drop_collection()
  helmgast = World(title=u"Helmgast", publisher=u"Helmgast", description=u"En helmgasts historia").save()
  mundana = World(title=u"Mundana", publisher=u"Neogames", description=u"En fantasyvärld för grisodling").save()
  altor = World(title=u"Altor", publisher=u"Niklas Fröjd", description=u"Drakar Demoner advanced").save()
  kult = World(title=u"Kult", publisher=u"Äventyrsspel", description=u"Demiurger och nefariter").save()

  # RelationType.drop_collection()
  RelationType(name=u"child of").save()
  RelationType(name=u"parent of").save()
  friend = RelationType(name=u"friend of").save()
  enemy = RelationType(name=u"enemy of").save()
  RelationType(name=u"distant relative of").save()

  # User.drop_collection()
  mf = User(username='martin', password=make_password('ljusbringaren'), email='ripperdoc@gmail.com', status=UserStatus.active,
    admin=True, realname='Martin F', description='Always games in a hat. Has a cat.').save()
  nf = User(username='niklas', password=make_password('fexiororden'), email='niklas@user.com', status=UserStatus.active,
    admin=True, realname='Niklas F').save()
  pf = User(username='per', password=make_password('liljansgarde'), email='per@user.com', status=UserStatus.active, admin=True,
    realname='Per F').save()
  mb = User(username='marco', password=make_password('carwelan'), email='marco@user.com', status=UserStatus.active, admin=False,
    realname='Marco B').save()
  fj = User(username='fredrik', password=make_password('luberosarv'), email='fredrik@user.com', status=UserStatus.active,
    admin=False, realname='Fredrik J').save()
  pd = User(username='paul', password=make_password('tiamelrenovel'), email='pauld@user.com', status=UserStatus.active, admin=False,
    realname='Paul D').save()
  pn = User(username='petter', password=make_password('thalamur'), email='petter@user.com', status=UserStatus.active,
    admin=False, realname='Petter N').save()
  aw = User(username='anton', password=make_password('rhakori'), email='anton@user.com', status=UserStatus.active,
    admin=False, realname='Anton W').save()

  ar = User(username='alex', password=make_password('asharien'), email='alex@user.com', status=UserStatus.active, admin=False,
    realname='Alex R').save()
  ks = User(username='krister', password=make_password('ebhronitiska'), email='krister@user.com', status=UserStatus.active,
    admin=False, realname='Krister S').save()
  User(username='calle', password=make_password('kraggbarbar'), email='calle@user.com', status=UserStatus.active, admin=False,
    realname='Carl-Johan S').save()
  mj = User(username='mattias', password=make_password('cirefalien'), email='mattias@user.com', status=UserStatus.active,
    admin=False, realname='Mattias J').save()
  rl = User(username='robin', password=make_password('consaber'), email='robin@user.com', status=UserStatus.active, admin=False,
    realname='Robin L').save()
  rj = User(username='rikard', password=make_password('rikard'), email='rikard@user.com', status=UserStatus.active,
    admin=False, realname='Rikard J').save()
  vs = User(username='victoria', password=make_password('victoria'), email='victoria@user.com', status=UserStatus.active,
    admin=False, realname='Victoria S').save()
  User(username='john', password=make_password('john'), email='john@user.com', status=UserStatus.active, admin=False,
    realname='John E').save()
  User(username='anders', password=make_password('anders'), email='anders@user.com', status=UserStatus.active,
    admin=False, realname='Anders D').save()
  jc = User(username='johan', password=make_password('johan'), email='johan@user.com', status=UserStatus.active, admin=False,
    realname='Johan C').save()
  cm = User(username='claes', password=make_password('claes'), email='claes@user.com', status=UserStatus.active, admin=False,
    realname='Claes M').save()
  dm = User(username='daniel', password=make_password('daniel'), email='daniel@user.com', status=UserStatus.active, admin=False,
    realname='Daniel M').save()
  jg = User(username='jonathan', password=make_password('jonathan'), email='jonathan@user.com', status=UserStatus.active,
    admin=False, realname='Jonathan G').save()
     
  mf.following = [nf, ks, ar, mb]
  mf.save()

  # Article.drop_collection()
    
  im = ImageAsset(creator=mj)
  im.make_from_url("http://kaigon.se/wiki/images/6/6b/Ljusets_son.jpg")
  # im.update_slug()
  im.save()
  Article(type='person',
    title=u"Ljusbringaren",
    content=u"Erövraren av världen, nedstigen från de astrala planen, med syftet att sprida ljus. Även kallad Edison.",
    world=altor,
    creator=rl,
    status=PublishStatus.published,
    persondata = PersonData(
      born=altor_date(1653,3,4),
      died=altor_date(1891,12,3),
      gender=GenderTypes.male,
      occupation=u"Ljusbringare")
    ).save()

  Article(type='blogpost',
    status=PublishStatus.published,
    title=u"Gift tills döden skiljer oss åt",
    world=mundana,
    creator=pn,
    content=
u"""
Nu har vi kommit tillbaka från den mörkaste tiden på året då de skotropiska krafterna har härjat fritt. Vår stora checklista som vi tog fram i början av hösten på "allt som måste göras" börjar nu komma ner i hanterliga mängder (en fingervisning är väl att 50 saker är kvar av 600).

Den här posten kommer däremot att kika lite på hur gifter kommer att fungera. De tidigare reglerna involverade lite för många slag och lite för mycket tidsräknande kring rundor, minuter, timmar och liknande. Vi ville behålla essensen men ändå göra det mer lätthanterligt.

Så här kan det därför fungera om man drabbas av ett bedövande gift: Under de följande tre rundorna kommer man att slå sin Livskraft mot svårigheten 12. Om man lyckas med slaget klarar man sig den rundan (för att gå helt opåverkad måste man alltså klara tre slag i rad). Om man misslyckas drabbas man av den första effekten, i detta fallet Omtöcknad (som ger temporärt avdrag likt Smärta). Andra gången man misslyckas blir effekten lite värre och om man skulle misslyckas tre gånger så blir man Utslagen.
"""
  ).save()
  Article(type='blogpost',
    status=PublishStatus.published,
    title=u"Monster",
    content=
u"""
Monster fungerar inte på samma sätt som människor och andra folkslag. När du får in en träff med morgonstjärnan som skulle sända tiraken hem till sin gudinna så får du hyggelmonstret att bli än mer uppretad och aggressiv. Monster är oförutsägbara och en del är så fulla av ursinne och adrenalin att smärta inte bekommer dem.

I Eon IV följer Monster (samt djur och liknande varelser) ett lite annorlunda skadesystem än vad vanliga folkslag gör. Det handlar både om att göra det enklare för en spelledare att administrera striderna men även att bidra med en annan känsla när man står öga mot öga med ett hyggelmonster på gladiatorarenans blodstänka sand. Istället för olika kroppsdelar och skadetabeller så har varje viktigare monster en egen skadetabell. På detta sätt finns det även variation mellan monster så att en strid mot ett halvdussin zombier blir en annan upplevelse än en strid mot ett grottroll. Skadetabellerna är också designade på ett annat sätt så om man slår lågt på dessa så råkar man ofta själv illa ut - så akta dig för det syraskvättande hyggelmonstret!
""",
    world=mundana,
    creator=nf).save()            

  Article(type='blogpost',
    status=PublishStatus.published,
    title=u"Gladiatorkämparna",
    content=
u"""
De två gladiatorkämparna Ademar och Brutus möts i den stora finalen i Jarum. Striden är på liv och död och guvernören har betalat stora pengar för att få se och bjuda på detta. Nedan är ett spelexempel mellan dessa två. Många regler har nämnts i tidigare blogginlägg men några är även nya här.

Striden börjar på Medellångt avstånd när då de befinner sig på motsatt sida av arenan. Ademar har en kastyxa hoppas kunna hota Brutus att agera i avståndsfasen och om inte annat skada honom. Ademar väljer att agera i avståndsfasen (och får därmed inte agera i närstridsfasen denna rundan). Brutus väljer det senare i hopp om att hinna fram till Ademar så snabbt som möjligt.

## Avståndsfasen
Avståndsfasen börjar och Ademar använder sin sidohandling för att dra sin kastyxa och sedan sin huvudhandling för att slunga iväg den mot Brutus som väljer att försvara sig med sin lilla rundsköld. Grundsvårigheten för Ademar är 10 (medellångt avstånd) vilket ökar till 14 på grund av skölden. Brutus slår sitt försvarsslag (med färdigheten Sköld) och spenderar samtidigt 1 Utmattning då han agerar utanför aktiv fas. Slaget landar på 16 vilket innebär att svårigheten för Ademar höjs till detta värde. Ademars har lite tur med Ob-slagen och får 23 - Brutus har blivit träffad! Det slumpas fram att Höger ben träffas (0 på 1T10) och Ademar har även fått ett Övertag på anfallet (23 är minst 5 mer än 16 men skillnaden är mindre än 10).

För detta Övertag ska Ademar välja en Fördel men för ett Övertag kan han endast välja Öka skada (då kastyxan inte har några vapengenskaper som ger rabatt på någon av de andra Fördelarna). Skadan blir därmed 2T6+3T6+2 = 5T6+2 i Huggskada (Grundskada + Vapenskada + Öka skada). Summan blir 21 och från detta subtraheras Brutus Grundrustning (3) samt hans pälsbyxors skydd mot Huggskada (2). Skadeverkan blir därmed 16 vilket hamnar inom intervallet 15-19. Detta orsakar dels 6 Utmattning samt ett slag på Skadetabellen för Huggskador i benen med 1T10+2. Ademar fortsätter att ha tur och får totalt 11.

Resultat 11 lyder "Träff över fotleden [Amputationsrisk 12 (fot).]". Brutus behöver alltså klara en svårighet på 12 eller få foten avhuggen! Han har tur med de 3T6 man slår och får 14 och klarar sig. Utöver detta blir Brutus totala Utmattning 7 (1 sedan innan) och han måste slå ett Chockslag mot denna som svårighet för att inte bli Utslagen. Han klarar detta galant det som hänt beskrivs färgglatt runt spelbordet.

## Närstridsfasen
Därefter börjar närstridsfasen som Brutus väljer att agera i. Han använder sin sidohandling för att Förflytta sig och då han vill ta sig två avstånd (från Medellångt via Kort till Närstrid) så måste han klara ett Förflyttningsslag. Svårigheten är mycket enkel (6) då det är stampad jord och sand på arenan och då Brutus inte är särskilt belastad i sin rustning klarar han det utan problem. Därefter öppnas närstriden. I vanliga fall hade Ademar och Brutus slagit sina Reaktionsslag för att se vem som börjar som anfallare men då Ademar redan har agerat i avståndsfasen så förlorar han denna automatiskt. Brutus använder därmed sin huvudhandling för att anfalla med sin storhammare och slår 22. Ademar försöker desperat blockera med sin sköld (–1T6 då han inte har den redo) och slår 15. På träfftabellen slår Brutus 3 och träffar därmed Torson.

Brutus får alltså ett Övertag. Storhammare har dock vapengenskaperna Klyvande 2 och Otymplig. Den första ger 2 Övertag rabatt på Fördelen Slå sönder och den andra gör det omöjligt att attackera med Snabbt anfall (Brutus gjorde ett standardanfall ovan). Slå sönder kostar normalt 3 Övertag men med rabatten kan Brutus köpa den för sitt enda Övertag vilket han också gör. Slå sönder fungerar mot utrustning som har vapenegenskapen Bräcklig, vilket de flesta sköldar har. Skölden blir därmed obrukbar (för striden, kan repareras senare) och Brutus går vidare med att slå hammarens Krosskada på 6T6 (varav 2T6 från Grundskada) och får totalt 25. Ademars totalt skydd mot Krosskada i torson är 5 så skadeverkan blir 20. Detta hamnar inom intervallet 20-24 vilket ger 8 Utmattning och ett slag på skadetabellen för krosskador i torson på 1T10+4.

Den ödesmättade tärningen slås, blir 8 och totalt resultat 12. En träff i torson är däremot mycket mer allvarlig än i armar och ben. Ademar måste direkt slå ett Dödsslag med svårighet 12 som han lyckas med. Därefter kommer beskrivningen "Träff i buken får maginnehållet att välla upp i munnen [Smärta, Omtöcknad.]". Även om själva träffen inte dödade Ademar så är han nu illa ute. Smärta ger –1T6 på alla slag och Omtöcknad fungerar liknande fast endast nästa runda. Den rundan kommer även Brutus fortsätta att vara anfallare då Ademar slog lägre på sitt försvarsslag (och inte hade möjlighet att välja några särskilda försvarstaktiker då han inte valde närstridsfasen som sin aktiva fas). Runt spelbordet beskrivs hur Ademars sköld knäcks och hur storhammare trycker rätt in i buken.

Här lämnar vi våra kämpar.
""",
    world=mundana,
    creator=nf).save()

  Product(title='Eon IV Grundbok',
          description='Grundbok för nya Eon',
          publisher='Helmgast AB',
          family='Eon',
          type=ProductTypes.book,
          price=419,
          status=ProductStatus.pre_order).save()

  Product(title='Helgonboken',
          description='Specialutgåva av grundbok för nya Eon',
          publisher='Helmgast AB',
          family='Eon',
          type=ProductTypes.book,
          price=1099,
          status=ProductStatus.pre_order).save()

  Product(title='Spelpaketet',
          description='Paket med crowdfunderunikt extramaterial',
          publisher='Helmgast AB',
          family='Eon',
          type=ProductTypes.book,
          price=399,
          status=ProductStatus.pre_order).save()

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

  scmpa = Article(type='campaign', title=u"Spelveckan", world=mundana, content=u"Deep drama at the beginning of July each year.").save()
  cd4ka = Article(type='campaign', title=u"Den Fjärde Konfluxen", world=altor, description=u"Rollpersonerna (Kandor, Zebbe, Navi, Josay och Titziana) är ordensmedlemmar i Yvainorden i staden Yavaris i Banborstland på Pandaros. Yvain är en av de fyra plågade hjältarna och hans ordnar kontrollerar mer eller mindre de civiliserade delarna av kontinenten.").save()
  cd6ka = Article(type='campaign', title=u"Den Sjätte Konfluxen", world=altor, description=u"Kampanjen handlar om professor Joseph Tiesen och hans expedition som sägs ha sänts ut av Kublai Shakkar, kejsare och arkon över Mergal. Expeditionen kommer att resa runt i både Jargal och Pandaros i jakt på allt som kan vara relevant för den kommande sjätte konfluxen.").save()
  kcmpa = Article(type='campaign', title=u"Kult AW", world=kult, description=u"Drama in victorian England at the edge of reality").save()
  ycmpa = Article(type='campaign', title=u"Yerlog", world=mundana, description=u"Time to take over the world!").save()

  ycmpa.relations = [ArticleRelation(relation_type=enemy, article=scmpa), ArticleRelation(relation_type=friend, article=kcmpa)]
  ycmpa.save()
  
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
