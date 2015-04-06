import os
import unittest
import tempfile

from flask.ext.mongoengine.wtf.models import ModelForm
from flask.ext.mongoengine.wtf import model_form

import raconteur
from controller.resource import ResourceHandler, ResourceRoutingStrategy
from raconteur import db


class TestObject(db.Document):
  name = db.StringField(max_length=60)


class CSRFDisabledModelForm(ModelForm):
  def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
    super(CSRFDisabledModelForm, self).__init__(formdata, obj, prefix, csrf_enabled=False, **kwargs)


class RaconteurTestCase(unittest.TestCase):
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
    handler.register_urls(raconteur.the_app, strategy)
    with raconteur.the_app.test_request_context(path='/test_objects/new', method="POST",
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
    self.db_fd, raconteur.the_app.config['DATABASE'] = tempfile.mkstemp()
    raconteur.the_app.config['TESTING'] = True
    self.app = raconteur.the_app.test_client()

  def tearDown(self):
    TestObject.drop_collection()
    os.close(self.db_fd)
    os.unlink(raconteur.the_app.config['DATABASE'])


def run_tests():
  unittest.main()


if __name__ == '__main__':
  run_tests()
