import os
import raconteur
import unittest
import tempfile

class RaconteurTestCase(unittest.TestCase):

	def test_empty_db(self):
		rv = self.app.get('/')
		assert 'Welcome to Raconteur' in rv.data

	def test_get_world(self):
		rv = self.app.get('/world/')
		assert 'any fictional world at your fingertips' in rv.data

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



if __name__ == '__main__':
	unittest.main()
