from models import User, GeneratorInputList, GeneratorInputItem

__author__ = 'Niklas'

from flask import   render_template, Blueprint
from peewee import *
from wtfpeewee.orm import model_form

from flask_peewee.utils import  object_list
import random
import itertools

from app import db

generator = Blueprint('generator', __name__, template_folder='templates')

@generator.route('/')
def index():
    return render_template('generator/index.html', list=generator_dictionary.keys(), sizes=generator_sizes)

@generator.route('/<name>/<num_results>')
def generate(name, num_results=10):
    # Lookup factory function which upon calls creates a string generator
    generator_factory_function = generator_dictionary.get(name)

    if generator_factory_function is None:
        return render_template('generator/generate.html', outputList=["Generator '"+name+"' does not exist"])
        
    # Merge functions into one output function, which is a generator
    out_gen = generator_factory_function()
    
    # Produce some number of unique entries and sort them
    outputList = produce_sorted_list(out_gen, int(num_results))

    # Render output
    return render_template('generator/generate.html', name=name, outputList=outputList)

def produce_sorted_list(iterable, list_size):
    return sorted(itertools.islice(unique_everseen(iterable), list_size))

def create_output_generator(iterables):
    def anon_func():
        return u''.join([gen() for gen in iterables])
    while True:
        yield anon_func()

def unique_everseen(iterable):
    seen = set()
    seen_add = seen.add
    for element in itertools.ifilterfalse(seen.__contains__, iterable):
        seen_add(element)
        yield element

def create_generator(inputList, odds = 1.0):
    def anon_func():
        if random.random() < odds:
            return random.choice(inputList)
        else:
            return u''
    return anon_func

def lookup_generator(generatorObject):
    # Use ID to differentiate between impls?
    def anon_func():
        if random.random() < odds:
            return random.choice(inputList)
        else:
            return u''
    return anon_func

def korhiv_generator():
    l1 = [i.content for i in GeneratorInputList.get(name=u'Korhiv start letter').items()]
    l2 = [i.content for i in GeneratorInputList.get(name=u'Korhiv middle syllables').items()]
    l3 = [i.content for i in GeneratorInputList.get(name=u'Korhiv end syllables').items()]
    
    r1 = create_generator(l1, 0.5)
    r2 = create_generator(l2)
    r3 = create_generator(l3)

    return create_output_generator([r1, r2, r3])

generator_dictionary = {'korhiv' : korhiv_generator}
generator_sizes = [10,20,50,100]
