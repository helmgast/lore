#!/usr/bin/env python
import os
import sys

is_debug = True
is_deploy = 'OPENSHIFT_INTERNAL_IP' in os.environ  # means we are running on OpenShift

# This is just a startup script for launching the server.

# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path

import raconteur

if __name__ == '__main__':
  if is_deploy:  # We're running on deployment server
    deploy.run()

  else:
    print "Running local %s" % __name__
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
      print "Resetting data models" # reloads DB with data specified in /test_data/model_setup.py
      raconteur.setup_models()
      exit()
    else:
      raconteur.the_app.run(debug=is_debug)  # Debug will reload code automatically, so no need to restart server
