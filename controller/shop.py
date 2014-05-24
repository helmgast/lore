"""
  controller.shop
  ~~~~~~~~~~~~~~~~

  This is the controller and Flask blueprint for a basic webshopg. It will
  setup the URL routes based on Resource and provide a checkout flow. It
  also hosts important return URLs for the payment processor.

  :copyright: (c) 2014 by Raconteur
"""
from flask import render_template, Blueprint, current_app
from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter, RacBaseForm
from model.shop import Product, Order
from flask.ext.mongoengine.wtf import model_form

logger = current_app.logger if current_app else logging.getLogger(__name__)

shop_app = Blueprint('shop', __name__, template_folder='../templates/shop')
product_strategy = ResourceAccessStrategy(Product, 'products', 'slug', 
  short_url=False, form_class=model_form(Product, base_class=RacBaseForm, 
  exclude=['slug'], converter=RacModelConverter()))

ResourceHandler.register_urls(shop_app, product_strategy)

order_strategy = ResourceAccessStrategy(Order, 'orders')

class OrderHandler(ResourceHandler):

  @ResourceHandler.methods(['POST'])
  def cart(self, r):
    return r

OrderHandler.register_urls(shop_app, order_strategy)

@shop_app.route('/')
def index():
    products = Product.objects()
    return render_template('shop/product_list.html', products=products)

# @shop_app.route('/cart')
# def cart():
#   return "Test"

### POST cart - add products, create order if needed
### GET cart - current order, displayed differently depending on current state

### my orders