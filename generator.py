from models import User

__author__ = 'Niklas'

from flask import   render_template, Blueprint
from peewee import *
from wtfpeewee.orm import model_form

from flask_peewee.utils import  object_list
import random

from app import db

def create_tables():
    StringGenerator.create_table(fail_silently=True)
    GeneratorRepeatRule.create_table(fail_silently=True)


class StringGenerator(db.Model):
    name = CharField()
    description = TextField()
    generator = None

    def __unicode__(self):
        return self.name

generator = Blueprint('generator', __name__, template_folder='templates')

@generator.route('/')
def index():
    print "Index"
    qr = StringGenerator.select()
    return object_list('generator/index.html', qr)


@generator.route('/<name>/generate')
def generate(name):
    try:
        generator = StringGenerator.get(name=name)
    except StringGenerator.DoesNotExist:
        generator = StringGenerator(name=name)

    repeat_rule = GeneratorRepeatRule.create(num_results=10, max_repeats=100)
    item_qualifier = NonDuplicateQualifier()
    generator_factory = ItemGeneratorFactory();
    simpleGenerator = ListGenerator(repeat_rule, item_qualifier, generator_factory)

    inputList = [u.realname for u in User.select()]
    outputList = simpleGenerator.generateList(inputList)
    return render_template('generator/generate.html', generator=generator, outputList=outputList)


class ItemGeneratorFactory():
    def createGenerator(self, inputList):
        # Use ID to differentiate between impls?
        return RandomChoiceGenerator(inputList)

# Decides how to produce one input from some input list
class RandomChoiceGenerator():
    def __init__(self, arg1):
        self.inputList = arg1

    def generateItem(self):
        return random.choice(self.inputList);

# Decides if an output entry is good enough, such as duplicate, lenght, etc
class NonDuplicateQualifier():
    def is_qualified(self, output, outputList):
        return output not in outputList

# Decides repetition of generator, what the desired output size is as well as maximum number of tries (if generator fails to produce qualified results)
class GeneratorRepeatRule(db.Model):
    num_results = IntegerField()
    max_repeats = IntegerField()

    def is_qualified(self, outputList):
        return len(outputList) >= self.num_results;

    def __unicode__(self):
        return "Results: " + self.num_results


# Wrapper class for creating several entries, ie a list
class ListGenerator():
    def __init__(self, arg1, arg2, arg3):
        self.repeat_rule = arg1
        self.item_qualifier = arg2
        self.generator_factory = arg3

    def generateList(self, inputList):
        outputList = []
        counter = 0
        item_generator = self.generator_factory.createGenerator(inputList)
        while self.may_continue(self.repeat_rule, outputList, counter):
            output = item_generator.generateItem()
            counter += 1
            if self.item_qualifier.is_qualified(output, outputList):
                outputList.append(output)
        return outputList

    def may_continue(self, outputQualifier, outputList, current_repeats):
        return len(outputList) < outputQualifier.num_results and\
               current_repeats < outputQualifier.max_repeats
