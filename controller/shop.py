"""
  controller.shop
  ~~~~~~~~~~~~~~~~

  This is the controller and Flask blueprint for a basic webshopg. It will
  setup the URL routes based on Resource and provide a checkout flow. It
  also hosts important return URLs for the payment processor.

  :copyright: (c) 2014 by Raconteur
"""
from flask import render_template, Blueprint, current_app, g, request
from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter, RacBaseForm
from model.shop import Product, Order
from flask.ext.mongoengine.wtf import model_form
import tasks

logger = current_app.logger if current_app else logging.getLogger(__name__)

shop_app = Blueprint('shop', __name__, template_folder='../templates/shop')
product_strategy = ResourceAccessStrategy(Product, 'products', 'slug', 
  short_url=False, form_class=model_form(Product, base_class=RacBaseForm, 
  exclude=['slug'], converter=RacModelConverter()))

ResourceHandler.register_urls(shop_app, product_strategy)

order_strategy = ResourceAccessStrategy(Order, 'orders')

class OrderHandler(ResourceHandler):

  @ResourceHandler.methods(['GET','POST'])
  def cart(self, r):
    if g.user:
      cart_order = Order.objects(user=g.user, status='cart').first()
      if not cart_order:
        cart_order = Order(user=g.user, email=g.user.email).save()
      r['item'] = cart_order
      r['order'] = cart_order
      r['url_args'] = {'order':cart_order.id}
    else:
      raise ResourceError(401, "Need to log in to use shopping cart")
    if request.method == 'GET':
      r = self.form_edit(r)
    elif request.method == 'POST':
      r = self.edit(r)
    r['template'] = 'shop/order_cart.html'
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
@shop_app.route('/download/<file>/')
def download(file):
  if current_app.celery:
    pdf_file = current_app.celery.fetch_pdf_eon_cf.delay('a', 'b')
    print "Test for %s" % file
    return pdf_file.get()
  else:
    logger.error("Celery has not been set up for tasks")
    abort(500)
