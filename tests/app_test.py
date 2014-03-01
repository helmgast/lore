import os
import raconteur
import unittest
import tempfile
import logging
from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter, ArticleBaseForm, ResourceError
from model.world import World
from raconteur import db

class TestObject(db.Document):
    name = db.StringField(max_length=60)

class RaconteurTestCase(unittest.TestCase):

	def test_strategy_simple(self):
		strategy = ResourceAccessStrategy(TestObject, 'test_objects', short_url=True)
		self.assertEqual('/test_objects', strategy.url_list())
		self.assertEqual('/test_objects/new', strategy.url_list('new'))
		self.assertEqual('/<testobject>', strategy.url_item())
		self.assertEqual('/<testobject>/edit', strategy.url_item('edit'))
		self.assertEqual('testobject_item.html', strategy.item_template())
		self.assertEqual('testobject_list.html', strategy.list_template())
		self.assertEqual('testobject_view', strategy.endpoint_name('view'))

	def test_strategy_query(self):
		strategy = ResourceAccessStrategy(TestObject, 'test_objects', short_url=True)
		obj = TestObject(name="test_name").save()
		self.assertIn(obj, strategy.query_list({"name":"test_name"}))
		self.assertEqual(0, len(strategy.query_list({"name":"test_name_1"})))
		self.assertEqual(1, len(strategy.query_list({"name_1":"test_name"}))) # Intentional?
		self.assertEqual({}, strategy.query_parents(**{"name":"test_name"}))
		self.assertEqual(TestObject(), strategy.create_item())
		self.assertEqual({'testobject': None}, strategy.all_view_args(TestObject()))

	def test_strategy_access(self):
		strategy = ResourceAccessStrategy(TestObject, 'test_objects', short_url=True)
		self.assertEqual(True, strategy.allowed_any('view'))
		obj = TestObject(name="test_name");
		self.assertEqual(True, strategy.allowed_on('edit', obj))

	def test_handler(self):
#		rv = self.app.get('/world/altor/articles/new')
		pass
		# handler = ResourceHandler(ResourceAccessStrategy(TestObject, 'test_objects', short_url=True))
		# with raconteur.the_app.test_request_context('/test_objects/new?name=test_name_handler'):
		# 	with self.assertRaises(ResourceError):
		# 		handler.new({'op':'new', 'url_args':{}})
		# 	self.assertEqual('/testresource', handler.new({'op':'new'}))

	def test_empty_db(self):
		rv = self.app.get('/')
		self.assertIn('Welcome to Raconteur', rv.data)

	def test_get_world(self):
		rv = self.app.get('/world/')
		self.assertIn('any fictional world at your fingertips', rv.data)

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
