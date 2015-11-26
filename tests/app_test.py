import os
import unittest
import tempfile

from flask.ext.mongoengine.wtf.models import ModelForm
from flask.ext.mongoengine.wtf import model_form

# Below 3 lines needed to be able to access fablr module
import sys
from os import path
sys.path.append( path.dirname( path.dirname( path.abspath(__file__) ) ) )

from fablr import app
from fablr.controller.resource import ResourceHandler, ResourceRoutingStrategy
from fablr.app import db


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
#

class TestObject(db.Document):
  name = db.StringField(max_length=60)


class CSRFDisabledModelForm(ModelForm):
  def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
    super(CSRFDisabledModelForm, self).__init__(formdata, obj, prefix, csrf_enabled=False, **kwargs)


class FablrTestCase(unittest.TestCase):
  def test_strategy_simple(self):
    strategy = ResourceRoutingStrategy(TestObject, 'test_objects', short_url=True)
    self.assertEqual('/test_objects', strategy.url_list())
    self.assertEqual('/test_objects/new', strategy.url_list('new'))
    self.assertEqual('/<testobject>', strategy.url_item())
    self.assertEqual('/<testobject>/edit', strategy.url_item('edit'))
    self.assertEqual('testobject_item.html', strategy.item_template())
    self.assertEqual('testobject_list.html', strategy.list_template())
    self.assertEqual('testobject_view', strategy.endpoint_name('view'))

  def test_strategy_query(self):
    strategy = ResourceRoutingStrategy(TestObject, 'test_objects', short_url=True)
    obj = TestObject(name="test_name").save()
    self.assertIn(obj, strategy.query_list({"name": "test_name"}))
    self.assertEqual(0, len(strategy.query_list({"name": "test_name_1"})))
    self.assertEqual(1, len(strategy.query_list({"name_1": "test_name"})))  # Intentional?
    self.assertEqual({}, strategy.query_parents(**{"name": "test_name"}))
    self.assertEqual(TestObject(), strategy.create_item())
    self.assertEqual({'testobject': None}, strategy.all_view_args(TestObject()))

  def test_strategy_access(self):
    strategy = ResourceRoutingStrategy(TestObject, 'test_objects', short_url=True)
    strategy.check_operation_any('view')
    obj = TestObject(name="test_name")
    strategy.check_operation_on('edit', obj)

  def test_handler(self):
    strategy = ResourceRoutingStrategy(TestObject, 'test_objects',
                                      form_class=model_form(TestObject, base_class=CSRFDisabledModelForm))
    handler = ResourceHandler(strategy)
    handler.register_urls(app.the_app, strategy)
    with app.the_app.test_request_context(path='/test_objects/new', method="POST",
                                                data={"name": "test_name_handler"}):
      result = handler.new({'op': 'new'})
      self.assertEqual('new', result['op'])
      self.assertEqual(u'test_name_handler', result['item'].name)

  def login(self, username, password):
    return self.app.post('/accounts/login/', data=dict(
      username=username,
      password=password
    ), follow_redirects=True)

  def logout(self):
    return self.app.get('/accounts/logout', follow_redirects=True)

  def setUp(self):
    self.db_fd, app.the_app.config['DATABASE'] = tempfile.mkstemp()
    app.the_app.config['TESTING'] = True
    self.app = app.the_app.test_client()

  def tearDown(self):
    TestObject.drop_collection()
    os.close(self.db_fd)
    os.unlink(app.the_app.config['DATABASE'])


def run_tests():
  unittest.main()


if __name__ == '__main__':
  unittest.main()
