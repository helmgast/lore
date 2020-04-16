import graphene
from graphene_mongo import MongoengineConnectionField, MongoengineObjectType
from .topics import Topic as TopicModel


class Topic(MongoengineObjectType):

    class Meta:
        model = TopicModel


class Query(graphene.ObjectType):
    topics = graphene.List(Topic)

    def resolve_topics(self, info):
        return list(TopicModel.objects.all())


schema = graphene.Schema(query=Query)
