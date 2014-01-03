# coding=utf-8

from model.campaign import *
from model.misc import *
from model.user import *
from model.world import *
from flask_peewee.utils import make_password
from peewee import drop_model_tables, create_model_tables
from test_data.model_setup import add_test_data
import sys
import inspect

def altor_date(year, month, day):
    return year*360+(month-1)*30+(day-1)

def get_models():
    models = [
        Session,
        Episode,
        CampaignInstance,
        ConversationMember,
        GroupMember,
        Message,
        Relationship,
        MediaArticle,
        PersonArticle,
        EventArticle,
        FractionArticle,
        CampaignArticle,
        RelationType,
        PlaceArticle,
        ArticleRelation,
        ArticleGroup,
        Group,
        Conversation,
        User,
        Article,
        World,
        StringGenerator,
        GeneratorInputList,
        GeneratorInputItem]

    # A little double checking, inspect the models module and list all classes, check that they correspond with models[]
    model_classes = inspect.getmembers(sys.modules['models'], inspect.isclass)
    model_classes = [m[1] for m in model_classes if m[1].__module__ == 'models']
    for m in model_classes:
        if m not in models:
            print "WARNING model_setup has not been told to setup this model: %s" % m 
    return models

def drop_tables(model_array):
    drop_model_tables(model_array, fail_silently=True)
    create_model_tables(model_array)

def setup_models():
    models = get_models()
    drop_tables(models)
    add_test_data()

