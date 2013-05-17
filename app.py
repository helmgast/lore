#!/usr/bin/env python
import os
import sys
from gevent import monkey; monkey.patch_all()

from raconteur_app import myapp
myapp.config['PROPAGATE_EXCEPTIONS'] = True

#
# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path
#
import deploy
import model_setup
#
#  main():
#
if __name__ == '__main__':
   #os.environ['OPENSHIFT_INTERNAL_IP'] = '127.0.0.1'
   if 'OPENSHIFT_INTERNAL_IP' in os.environ:
      deploy.run()
   else:
      print "Running local"
      if len(sys.argv) > 1 and sys.argv[1] == "reset":
         print "Resetting data models"
         model_setup.setup_models()
         exit()
      myapp.run(debug=True) # Debug will reload code automatically, so no need to restart server