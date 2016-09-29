"""
    model.campaign
    ~~~~~~~~~~~~~~~~

    Provides Mongoengine model classes for all game campaign related features.

    :copyright: (c) 2014 by Helmgast AB
"""

from misc import Document  # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, DateTimeField, ReferenceField, BooleanField, ListField,
                         EmbeddedDocumentField)

from user import User, Group
from world import Article


# A game session that was or will be held, e.g. the instance between a scenario
# and a group  at a certain date
class Session(EmbeddedDocument):
    play_start = DateTimeField()
    play_end = DateTimeField()
    location = StringField()  # Location of the session
    description = StringField()  # Details on the event if any.
    # episodes = ListField(ReferenceField(Episode))
    episodes = ListField(StringField())
    present_members = ListField(ReferenceField(User));

    def __unicode__(self):
        return u'Session of %s at %s' % ('self.campaign', self.play_start.strftime('%Y-%m-%d'))


# All material related to a certain story by a certain group.
class CampaignInstance(Document):
    campaign = ReferenceField(Article)  # CampaignData
    group = ReferenceField(Group)
    rule_system = StringField()
    description = StringField()
    archived = BooleanField(default=False)  # If the campaign is archived
    sessions = ListField(EmbeddedDocumentField(Session))
    chronicles = ListField(ReferenceField(Article))  # ChronicleArticles

    def __unicode__(self):
        return u'%s by %s' % (self.campaign.title, self.group)

# def load_scene_tree(self, scene_tree, parent=None):
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
# class Scene(Document):
#     campaign = ReferenceField(CampaignInstance)
#     parent = ReferenceField('self', related_name='children', )
#     name = StringField()
#     description = StringField()
#     order = IntField() # The integer order between scenes
#
#     def ordered_children(self):
#         return self.children.order_by(Scene.order.asc())
#
#     def __unicode__(self):
#         return u'Scene: %s of %s' % (self.name, self.campaign)

# Lists users present at a particular session
# class SessionPresentUser(Document):
#     present_user = ReferenceField(User)
#     session = ReferenceField(Session)
#
