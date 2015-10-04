"""
    model.campaign
    ~~~~~~~~~~~~~~~~

    Provides Mongoengine model classes for all game campaign related features.

    :copyright: (c) 2014 by Helmgast AB
"""

from fablr.app import db
from world import Article, Episode, User, Group

# A game session that was or will be held, e.g. the instance between a scenario
# and a group  at a certain date
class Session(db.EmbeddedDocument):
    play_start = db.DateTimeField()
    play_end = db.DateTimeField()
    location = db.StringField() # Location of the session
    description = db.StringField() # Details on the event if any.
    # episodes = db.ListField(db.ReferenceField(Episode))
    episodes = db.ListField(db.StringField())
    present_members = db.ListField(db.ReferenceField(User));

    def __unicode__(self):
        return u'Session of %s at %s' % ('self.campaign', self.play_start.strftime('%Y-%m-%d'))


# All material related to a certain story by a certain group.
class CampaignInstance(db.Document):
    campaign = db.ReferenceField(Article) # CampaignData
    group = db.ReferenceField(Group)
    rule_system = db.StringField()
    description = db.StringField()
    archived = db.BooleanField(default=False) # If the campaign is archived
    sessions = db.ListField(db.EmbeddedDocumentField(Session))
    chronicles = db.ListField(db.ReferenceField(Article)) # ChronicleArticles

    def __unicode__(self):
        return u'%s by %s' % (self.campaign.title, self.group)

#     def load_scene_tree(self, scene_tree, parent=None):
#         # TODO very inefficient implementation
#         o = 1
#         for s in scene_tree:
#             print "Found %s, updating to o=%s, parent=%s" % (s, o, parent)
#             q = Scene.update(order=o, parent=parent).where(Scene.id == s['id'])
#             print q.execute()
#             o += 1
#             if 'children' in s:
#                 self.load_scene_tree(s['children'], parent=Scene.get(Scene.id == s['id'])) 

# A part of a Scenario, that can be in current focus of a game
# class Scene(db.Document):
#     campaign = db.ReferenceField(CampaignInstance)
#     parent = db.ReferenceField('self', related_name='children', )
#     name = db.StringField()
#     description = db.StringField()
#     order = db.IntField() # The integer order between scenes
# 
#     def ordered_children(self):
#         return self.children.order_by(Scene.order.asc())
# 
#     def __unicode__(self):
#         return u'Scene: %s of %s' % (self.name, self.campaign)
                
# Lists users present at a particular session
# class SessionPresentUser(db.Document):
#     present_user = db.ReferenceField(User)
#     session = db.ReferenceField(Session)
#             