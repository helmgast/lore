#!/usr/bin/env python
import os
import sys

is_debug = True
is_deploy = 'OPENSHIFT_INTERNAL_IP' in os.environ  # means we are running on OpenShift

# This is just a startup script for launching the server.

# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path

import raconteur
import logging

if __name__ == '__main__':
  if is_deploy:  # We're running on deployment server
    deploy.run()

  else:
    # sys.argv = [sys.argv[0], "reset"];
    # sys.argv = [sys.argv[0], "test"];
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
      logging.basicConfig(level=logging.DEBUG)
      raconteur.setup_models() # Reloads DB with data specified in /test_data/model_setup.py
      exit()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
      logging.basicConfig(level=logging.DEBUG)
      raconteur.run_tests() # Runs all unit tests
    elif len(sys.argv) > 1 and sys.argv[1] == "lang":
      os.system("pybabel compile -d translations/");
      exit()
    else:
      logging.basicConfig(level=logging.DEBUG)
      raconteur.run_the_app(debug=is_debug) # Debug will reload code automatically, so no need to restart server
