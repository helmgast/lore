import os
import unittest
import tempfile

from flask.ext.mongoengine.wtf.models import ModelForm
from flask.ext.mongoengine.wtf import model_form

# Below 3 lines needed to be able to access fablr module
import sys
from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )

from fablr.app import create_app
from flask.ext.mongoengine import Document
from mongoengine import EmbeddedDocument, StringField
from werkzeug.datastructures import ImmutableMultiDict

# Find good set of dummy / dangerous data to populate with, e.g. special chars,
# html, scripts, etc

# What to test
# Password login
# Google login
# Facebook login
# Remind password (email received?)
# Logout
# Access (is an admin, gets admin)
# Access (is a user, dont get admin)
# Register user, user exist
# Register user, email sent
# Password length
# Username length and contents
# 404 - generate and test all URLs?
# User can change password
# User cannot change other user password
# That PDF fingerprinting works, test some different PDFs

class CSRFDisabledModelForm(ModelForm):
  def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
    super(CSRFDisabledModelForm, self).__init__(formdata, obj, prefix, csrf_enabled=False, **kwargs)

class TestObject(Document):
  name = StringField(max_length=60)

class FablrTestCase(unittest.TestCase):

  def test_forms(self):
      from wtforms.fields import HiddenField, FieldList, FormField
      class TestItemForm(self.RacBaseForm):
          prod = HiddenField()
          price = HiddenField()

      class TestListForm(self.RacBaseForm):
          thelist = FieldList(FormField(TestItemForm))

      class TestListObj(object):
          def __init__(self, alist):
              self.thelist = alist

      class OL(object):
          def __init__(self, prod, price):
              self.prod = prod
              self.price = price
          def __repr__(self):
              return "%s:%s" % (self.prod, self.price)
          def __eq__(self, other):
            return (isinstance(other, self.__class__) and self.__dict__ == other.__dict__)

      formdata = ImmutableMultiDict({
          'thelist-1-prod':'a',
          'thelist-1-price':'3',
          'thelist-2-prod':'b',
          'thelist-2-price':'3'
          })

      # TODO cannot handle Int conversion yet so we use strings for numbers too, or they wont count as equal
      obj = TestListObj([OL('a','1'),OL('b','2'),OL('c','3')])
      form = TestListForm(formdata, obj=obj)
      self.assertEqual(OL('a','1'), OL('a','1'))
      self.assertEqual(obj.thelist, [OL('a','1'),OL('b','2'),OL('c','3')])
      print "Obj before %s" % obj.thelist
      print "Form was %s" % form.data
      form.populate_obj(obj)
      print "Obj after %s" % obj.thelist
      self.assertEqual(obj.thelist, [OL('a','3'),OL('b','3')])

  def test_strategy_simple(self):
    strategy = self.ResourceRoutingStrategy(TestObject, 'test_objects', short_url=True)
    # Test that a strategy correctly sets up url routes
    self.assertEqual('/test_objects/', strategy.url_list())
    self.assertEqual('/test_objects/new', strategy.url_list('new'))
    self.assertEqual('/<testobject>/', strategy.url_item())
    self.assertEqual('/<testobject>/edit', strategy.url_item('edit'))
    self.assertEqual('testobject_item.html', strategy.item_template())
    self.assertEqual('testobject_list.html', strategy.list_template())
    self.assertEqual('testobject_view', strategy.endpoint_name('view'))

  def test_strategy_query(self):
    strategy = self.ResourceRoutingStrategy(TestObject, 'test_objects', short_url=True)
    obj = TestObject(name="test_name").save()
    self.assertIn(obj, strategy.query_list({"name": "test_name"}))
    self.assertEqual(0, len(strategy.query_list({"name": "test_name_1"})))
    self.assertEqual(1, len(strategy.query_list({"name_1": "test_name"})))
    self.assertEqual({}, strategy.query_parents(**{"name": "test_name"}))
    self.assertAlmostEqual(type(TestObject()), type(strategy.create_item()))
    self.assertEqual({'testobject': None}, strategy.all_view_args(TestObject()))

  def test_handler(self):
    strategy = self.ResourceRoutingStrategy(TestObject, 'test_objects',
                                      form_class=model_form(TestObject))
    handler = self.ResourceHandler(strategy)
    handler.register_urls(self.app, strategy)
    with self.app.test_request_context(path='/test_objects/new', method="POST", data={"name": "test_name_handler"}):
      self.app.preprocess_request() # Correctly sets up auth, etc
      result = handler.new({'op': 'new'})
      self.assertEqual('new', result['op'])
      self.assertEqual(u'test_name_handler', result['item'].name)

  def login(self, username, password):
    return self.client.post('/accounts/login/', data=dict(
      username=username,
      password=password
    ), follow_redirects=True)

  def logout(self):
    return self.client.get('/accounts/logout', follow_redirects=True)

  def setUp(self):
    # PRESERVE_CONTEXT... needed for avoiding context pop error, see
    # http://stackoverflow.com/questions/26647032/py-test-to-test-flask-register-assertionerror-popped-wrong-request-context
    # WTF_CSRF_CHECK_DEFAULT turn off all CSRF, test that in specific case only
    self.app = create_app(TESTING=True, PRESERVE_CONTEXT_ON_EXCEPTION=False, WTF_CSRF_CHECK_DEFAULT=False)
    self.client = self.app.test_client()
    # we need to fix imports here because the need app data at load time
    from fablr.controller.resource import ResourceRoutingStrategy, ResourceHandler, RacBaseForm
    self.ResourceRoutingStrategy = ResourceRoutingStrategy
    self.ResourceHandler = ResourceHandler
    self.RacBaseForm = RacBaseForm
    TestObject.drop_collection() # Ensure clean slate

  def tearDown(self):
    pass
    # TestObject.drop_collection()
    # os.close(self.db_fd)
    # os.unlink(app.the_app.config['DATABASE'])

def run_tests():
  unittest.main()

if __name__ == '__main__':
  unittest.main()
