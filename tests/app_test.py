import os
import raconteur
import unittest
import tempfile
import logging
from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter, ArticleBaseForm
from model.world import World

class RaconteurTestCase(unittest.TestCase):

	def test_strategy(self):
		strategy = ResourceAccessStrategy(World, 'testresource', 'slug', short_url=True)
		self.assertEqual('/testresource', strategy.url_list())

	def test_handler(self):
		handler = ResourceHandler(ResourceAccessStrategy(World, 'testresource', 'slug', short_url=True))
		# self.assertEqual('/testresource', handler.form_new({}))

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
		os.close(self.db_fd)
		os.unlink(raconteur.the_app.config['DATABASE'])


def run_tests():
	unittest.main()

if __name__ == '__main__':
	run_tests()
