import imp
import os
import sys

class DeployConfiguration(object):
    DATABASE = {
        'user': 'admin',
        'password': 'xzUqQfsuJlhN',
        'host':os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'],
        'port':os.environ['OPENSHIFT_POSTGRESQL_DB_PORT'],
        'name': 'raconteur',
        'engine': 'peewee.PostgresqlDatabase',
        'threadlocals': True,
        #'check_same_thread': False,
    }
    SECRET_KEY = 'shhhh'

PYCART_DIR = ''.join(['python-', '.'.join(map(str, sys.version_info[:2]))])

try:
   zvirtenv = os.path.join(os.environ['OPENSHIFT_HOMEDIR'], PYCART_DIR,
                           'virtenv', 'bin', 'activate_this.py')
   execfile(zvirtenv, dict(__file__ = zvirtenv) )
except IOError:
   pass

def run_gevent_server(app, ip, port=8080):
   from gevent.pywsgi import WSGIServer
   WSGIServer((ip, port), app).serve_forever()

def run_simple_httpd_server(app, ip, port=8080):
   from wsgiref.simple_server import make_server
   make_server(ip, port, app).serve_forever()

def run():
  ip   = os.environ['OPENSHIFT_INTERNAL_IP']
  port = 8080
  zapp = imp.load_source('application', 'wsgi/application')
  import raconteur

  #  Use gevent if we have it, otherwise run a simple httpd server.
  print 'Starting WSGIServer on %s:%d ... ' % (ip, port)
  try:
    run_gevent_server(raconteur.the_app, ip, port)
  except:
    print 'gevent probably not installed - using default simple server ...'
    run_simple_httpd_server(zapp.application, ip, port)