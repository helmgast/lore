#!/usr/bin/env python
import os
import sys

# This is just a startup script for launching the server locally.

# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path

from raconteur import create_app, init_actions
import logging

if __name__ == '__main__':
  mode = sys.argv[1] if len(sys.argv)>1 else None
  if mode:
    app = create_app(DEBUG=True)
    init_actions(app, mode)
    exit()
  else:
    app = create_app(DEBUG=True)
    app.run()  # Debug will reload code automatically, so no need to restart server