from setuptools import setup

setup(name='Raconteur', version='0.3',
      description='OpenShift application',
      author='Martin Frojd', author_email='ripperdoc@gmail.com',
      url='http://www.python.org/sigs/distutils-sig/',

      #  Uncomment one or more lines below in the install_requires section
      #  for the specific client drivers/modules your application needs.
      install_requires=[
            'Jinja2', 'Flask', 'flask-mongoengine', 'flask-peewee'
      ],
     )