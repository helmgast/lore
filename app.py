#!/usr/bin/env python
import os
import sys

is_debug = True
is_deploy = 'OPENSHIFT_INTERNAL_IP' in os.environ  # means we are running on OpenShift

# http://flask-peewee.readthedocs.org/en/latest/gevent.html#monkey-patch-the-thread-module
if is_deploy:  # Supposed patch to make gevent run better with peewee?
  from gevent import monkey; monkey.patch_all()
  import deploy

# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path

import raconteur

#
#  main():
if __name__ == '__main__':
  if is_deploy:  # We're running on deployment server
    raconteur.setup_models()
    #deploy.run()

  else:
    print "Running local %s" % __name__
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
      print "Resetting data models"
      raconteur.setup_models()
      exit()
    else:
      raconteur.the_app.run(debug=is_debug)  # Debug will reload code automatically, so no need to restart server
