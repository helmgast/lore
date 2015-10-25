#!/usr/bin/env python
import os
import sys
import subprocess

# This is just a startup script for launching the server locally.

from fablr.app import create_app
import logging

# Try to get app version from git in working directory
try:
    version = subprocess.check_output(["git", "describe","--always"])
    version = version.strip()
except subprocess.CalledProcessError:
    print >> sys.stderr, "Error getting git version"
if __name__ == '__main__':
  # This is run when executed from terminal
  mode = sys.argv[1] if len(sys.argv)>1 else None
  kwargs = {'VERSION':version}
  if mode=='nodebug':
    app = create_app(DEBUG=False, **kwargs)
    app.run()
  elif mode=='profile':
    from werkzeug.contrib.profiler import ProfilerMiddleware
    app = create_app(DEBUG=True, **kwargs)
    app.config['PROFILE'] = True
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30])
    app.run()  # Debug will reload code automatically, so no need to restart server
  else:
    app = create_app(DEBUG=True, **kwargs)
    app.run()  # Debug will reload code automatically, so no need to restart server
else:
  # This is run by UWSGI on the server
  app = create_app(**kwargs)
