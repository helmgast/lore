"""
  controller.shop
  ~~~~~~~~~~~~~~~~

  This is the controller and Flask blueprint for a basic webshopg. It will
  setup the URL routes based on Resource and provide a checkout flow. It
  also hosts important return URLs for the payment processor.

  :copyright: (c) 2014 by Raconteur
"""
import os

from flask import render_template, Blueprint, current_app, g, request, abort, send_file
import re
from flask.helpers import send_from_directory

from resource import ResourceHandler, ResourceAccessStrategy, RacModelConverter, RacBaseForm, ResourceError
from model.shop import Product, Order, OrderLine, OrderStatus
from flask.ext.mongoengine.wtf import model_form
import tasks

logger = current_app.logger if current_app else logging.getLogger(__name__)

shop_app = Blueprint('shop', __name__, template_folder='../templates/shop')
product_strategy = ResourceAccessStrategy(Product, 'products', 'slug', 
  short_url=False, form_class=model_form(Product, base_class=RacBaseForm, 
  exclude=['slug'], converter=RacModelConverter()))

ResourceHandler.register_urls(shop_app, product_strategy)

order_strategy = ResourceAccessStrategy(Order, 'orders')

# This injects the "cart_items" into templates in shop_app
@shop_app.context_processor
def inject_cart():
    cart_order = Order.objects(user=g.user, status=OrderStatus.cart).only('total_items').first()
    return dict(cart_items=cart_order.total_items if cart_order else 0)

cartform = model_form(Order, base_class=RacBaseForm, only=['order_lines'])

class OrderHandler(ResourceHandler):

  @ResourceHandler.methods(['GET','POST'])
  def cart(self, r):
    if g.user:
      cart_order = Order.objects(user=g.user, status=OrderStatus.cart).first()
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
      if request.form.has_key('product'):
        slug = request.form.get('product')
        p = Product.objects(slug=slug).first()
        if p:
          found = False
          for ol in cart_order.order_lines:
            if ol.product == p:
              ol.quantity = ol.quantity + 1
              found = True
          if not found: # create new orderline with this product
            newol = OrderLine(product=p, price=p.price)
            cart_order.order_lines.append(newol)
          cart_order.save()
          r['item'] = cart_order.total_items
        else:
          raise ResourceError(400, r, 'No product with slug %s exists' % slug)
      else:
        raise ResourceError(400, r, 'Not supported')

    r['template'] = 'shop/order_item.html'
    return r

OrderHandler.register_urls(shop_app, order_strategy)

@shop_app.route('/')
def index():
    products = Product.objects()
    return render_template('shop/product_list.html', products=products)

### POST cart - add products, create order if needed
### GET cart - current order, displayed differently depending on current state

### my orders
@shop_app.route('/eon-iv-pdf/')
def eon_iv_pdf():
  file_name = "Eon_IV_%s.pdf" % re.sub(r'@|\.', '_', g.user.email)
  directory = os.path.join(current_app.root_path, "resources", "pdf")
  if os.path.exists(os.path.join(directory, file_name)):
    return send_from_directory(directory, file_name)
  else:
    abort(404)

@current_app.template_filter('currency')
def currency(value):
  return ("{:.0f}" if float(value).is_integer() else "{:.2f}").format(value)
