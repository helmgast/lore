Openshift runs "gears" which are a kind of virtual environments on a Red Hat Linux environment. A gear contains "cartridges" which are ready-made applications, such as Python and MongoDB. In our case, we are running Python 2.7.

In a dev environment, we will manually call the the_app.run() which starts it's own webserver. But in deployed environment we will want to use a better webserver. There are some options, but a simple one is mod_wsgi from Apache. It will have Apache as the webserver, which will in turn call on the Python application. This has been hard-coded in Openshift to call:
myrepo/wsgi/application
it also has a directory
myrepo/wsgi/static
where Apache will serve normal files (e.g. images, css, etc).
The wsgi/application will only need to setup the virtualenv, and then call the the_app application. WSGI will be using a different method than run(), which is implicit but is called wsgi_app().

https://www.openshift.com/blogs/build-your-app-on-openshift-using-flask-sqlalchemy-and-postgresql-92

It's important that the app.py file used in developmen has the line:
if __name__ == '__main__':
as it will make sure when the file is imported, it will not execute the_app.run().

When we do a push to the OpenShift repository, it will have post-commit hooks which will run scripts on the server, which will both make sure to update dependencies (because the repository does not contain our dependencies) and which will run the application starter when completed. The server will run setup.py to know what dependencies there are.


To update, do:
    git push live

To drop postgresql database:
    dropdb -U admin <database>

To create a new postgresql database:
    createdb -U admin <database>

To tail the log of processes running (requires rhc command line tool from OpenShift)
    rhc tail -a raconteur

To start or stop app
rhc app stop raconteur
rhc app start raconteur



sudo apt-get update
sudo apt-get install apache2

sudo apt-get install libapache2-mod-wsgi

sudo a2enmod wsgi

sudo apt-get install python-dev

sudo apt-get install python-pip
sudo pip install virtualenvmkdir /var/www/helmgast.semkdir /var/repo/fablr.git/sudo apt-get install git

sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/ubuntu-upstart dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
sudo apt-get update
sudo apt-get install mongodb-10gen

sudo vi post-receive
#!/bin/sh
git --work-tree=/var/www/domain.com --git-dir=/var/repo/site.git checkout -f

chmod +x post-receive

sudo groupadd vpsadmin
sudo usermod -a -G vpsadmin martin
sudo usermod -a -G vpsadmin niklas

sudo chgrp -R /var/www/helmgast.se
sudo chmod -R 771 /var/www/helmgast.se
sudo chgrp -R /var/repo/fablr.git
sudo chmod -R 771 /var/repo/fablr.git

mkdir -p .ssh/

vi /etc/ssh/sshd_config

-Change settings to

PermitRootLogin no
PasswordAuthentication no
X11Forwarding no
UsePAM no
UseDNS no
AllowUsers michael