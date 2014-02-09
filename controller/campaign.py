from flask import request, redirect, url_for, render_template, Blueprint, flash
from resource import ResourceHandler, ResourceAccessStrategy
from model.campaign import *
 
campaign_app = Blueprint('campaign', __name__, template_folder='../templates/campaign')

campaign_handler = ResourceHandler(ResourceAccessStrategy(CampaignInstance, 'campaigns'))
campaign_handler.register_urls(campaign_app)
campaign_handler.register_index(campaign_app)