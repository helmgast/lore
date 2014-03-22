#!/usr/bin/env python
import os
import sys

is_debug = True
skip_model_validation = is_debug

# This is just a startup script for launching the server locally.

# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path

import raconteur
import logging

if __name__ == '__main__':
  if len(sys.argv) > 1 and sys.argv[1] == "reset":
    logging.basicConfig(level=logging.DEBUG)
    raconteur.setup_models()  # Reloads DB with data specified in /test_data/model_setup.py
    exit()
  elif len(sys.argv) > 1 and sys.argv[1] == "test":
    logging.basicConfig(level=logging.DEBUG)
    raconteur.run_tests()  # Runs all unit tests
  elif len(sys.argv) > 1 and sys.argv[1] == "lang":
    os.system("pybabel compile -d translations/")
    exit()
  else:
    logging.basicConfig(level=logging.DEBUG)
    if skip_model_validation or raconteur.validate_model():
      raconteur.run_the_app(debug=is_debug)  # Debug will reload code automatically, so no need to restart server
