#!/usr/bin/env python
import os
import sys

# This is just a startup script for launching the server locally.

from fablr.app import create_app
import logging

if __name__ == '__main__':
  # This is run when executed from terminal
  mode = sys.argv[1] if len(sys.argv)>1 else None
  if mode=='nodebug':
    app = create_app(DEBUG=False)
    app.run()
  elif mode=='profile':
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app = create_app(DEBUG=True)
    app.config['PROFILE'] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    app.run()  # Debug will reload code automatically, so no need to restart server
  else:
    app = create_app(DEBUG=True)
    app.run()  # Debug will reload code automatically, so no need to restart server
else:
  # This is run by UWSGI on the server
  app = create_app()