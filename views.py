import datetime

from flask import request, redirect, url_for, render_template, flash

from app_shared import app,auth
from models import User

@app.route('/')
def homepage():
  return render_template('homepage.html')
    #if auth.get_logged_in_user():
    #    return private_timeline()
    #else:
    #    return public_timeline()

# Page to sign up, takes both GET and POST so that it can save the form
@app.route('/join/', methods=['GET', 'POST'])
def join():
    if request.method == 'POST' and request.form['username']:
        # Read username from the form that was posted in the POST request
        try:
            user = User.get(username=request.form['username'])
            flash('That username is already taken')
        except User.DoesNotExist:
            user = User(
                username=request.form['username'],
                email=request.form['email'],
                join_date=datetime.datetime.now()
            )
            user.set_password(request.form['password'])
            user.save()
            
            auth.login_user(user)
            return redirect(url_for('homepage'))

    return render_template('join.html')