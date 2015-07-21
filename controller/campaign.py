"""
    controller.campaign
    ~~~~~~~~~~~~~~~~

    This is the controller and Flask blueprint for game campaign features,
    it initializes URL routes based on the Resource module and specific
    ResourceRoutingStrategy for each campaign related model class. This module is then
    responsible for taking incoming URL requests, parse their parameters,
    perform operations on the Model classes and then return responses via 
    associated template files.

    :copyright: (c) 2014 by Raconteur
"""

from flask import request, redirect, url_for, render_template, Blueprint, flash
from controller.resource import ResourceHandler, ResourceRoutingStrategy
from model.campaign import *
 
campaign_app = Blueprint('campaign', __name__, template_folder='../templates/campaign')

campaign_strategy = ResourceRoutingStrategy(CampaignInstance, 'campaigns')
ResourceHandler.register_urls(campaign_app, campaign_strategy)

@campaign_app.route('/')
def index():
    campaigns = CampaignInstance.objects()
    return render_template('campaign/campaigninstance_list.html', campaigns=campaigns)