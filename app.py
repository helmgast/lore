#!/usr/bin/env python
import imp
import os
import sys
from flask import Flask
myapp = Flask(__name__)
myapp.config['PROPAGATE_EXCEPTIONS'] = True

@myapp.route('/')
def hello_world():
    return "Hello World!"

#os.environ['OPENSHIFT_INTERNAL_IP'] = '127.0.0.1'
#
# IMPORTANT: Put any additional includes below this line.  If placed above this
# line, it's possible required libraries won't be in your searchable path
#
import deploy

#
#  main():
#
if __name__ == '__main__':
   if 'OPENSHIFT_INTERNAL_IP' in os.environ:
      deploy.run()
   