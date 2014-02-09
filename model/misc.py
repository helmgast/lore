from raconteur import db
import re
import datetime

'''
Created on 2 jan 2014

@author: Niklas
'''

# WTForms would treat the _absence_ of a field in POST data as a reason to
# to set the data to empty. This is a problem if the same POST receives variations
# to a form. This method removes form fields if they are not present in postdata.
# This means the form logic will not touch those fields in the actual objects.
def matches_form(formclass, formdata):
    for k in formdata.iterkeys():
        if k in dir(formclass):
            print "Matches field %s!" % k
            return True
    return False
  
def slugify(s):
    return re.sub('[^a-z0-9_\-]+', '-', s.lower())
  
def now():
    return datetime.datetime.now;

class GeneratorInputList(db.Document):
    name = db.StringField()

    def items(self):
        return GeneratorInputItem.select().where(GeneratorInputItem.input_list == self)

class GeneratorInputItem(db.Document):
    input_list = db.ReferenceField(GeneratorInputList)
    content = db.StringField()

class StringGenerator(db.Document):
    name = db.StringField()
    description = db.StringField()
    generator = None

    def __unicode__(self):
        return self.name

