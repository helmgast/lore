from flask import request, redirect, url_for, render_template, Blueprint, flash
from resource import ResourceHandler, ResourceAccessStrategy
from model.campaign import *
 
campaign_app = Blueprint('campaign', __name__, template_folder='../templates/campaign')

campaign_strategy = ResourceAccessStrategy(CampaignInstance, 'campaigns')
ResourceHandler.register_urls(campaign_app, campaign_strategy)

@campaign_app.route('/')
def index():
    campaigns = CampaignInstance.objects()
    return render_template('campaign/campaigninstance_list.html', campaigns=campaigns)