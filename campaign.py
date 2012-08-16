from flask import request, redirect, url_for, render_template, Blueprint, flash
from auth import auth
from flask_peewee.utils import get_object_or_404, object_list, slugify

campaign = Blueprint('campaign', __name__, template_folder='templates')

@campaign.route('/')
@auth.login_required
def index():
    return render_template('campaign/index.html')