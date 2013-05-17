import imp
import os
import sys
from app import myapp

if 'OPENSHIFT_INTERNAL_IP' in os.environ:
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

  #  Use gevent if we have it, otherwise run a simple httpd server.
  print 'Starting WSGIServer on %s:%d ... ' % (ip, port)
  try:
    run_gevent_server(myapp, ip, port)
  except:
    print 'gevent probably not installed - using default simple server ...'
    run_simple_httpd_server(zapp.application, ip, port)