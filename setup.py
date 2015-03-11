#!/usr/bin/env python
from setuptools import setup

setup(
    name='Raconteur', 
    version='0.6-webshop',
    description='Storytelling platform',
    author='Helmgast AB',
    author_email='info@helmgast.se',
    url='http://helmgast.se',

    #  Packages required to run Raconteur.
    install_requires=[
        'Flask', 'flask-mongoengine', 'python-slugify', 'Flask-Markdown', 
        'requests', 'Pillow', 'flask-babel', 'bugsnag', 'Flask-Mail', 'celery',
        'google-api-python-client', 'facebook-sdk'
    ],

    # Configures babel so we translate direct for setup.py.
    # "." means local directory - settings need to be specified per directory
    # Added Jinja extensions need to be reflected below
    message_extractors = {
        '.': [
            ('**.py',                'python', None),
            ('**/templates/**.html',  'jinja2', 
                {'silent':'false',
                'extensions':'jinja2.ext.do'})
        ],
    },
)