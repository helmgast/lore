"""
  controller.shop
  ~~~~~~~~~~~~~~~~

  This is the controller and Flask blueprint for a basic webshopg. It will
  setup the URL routes based on Resource and provide a checkout flow. It
  also hosts important return URLs for the payment processor.

  :copyright: (c) 2014 by Helmgast AB
"""
import os
import re
import stripe

from flask import render_template, Blueprint, current_app, g, request, abort, send_file, redirect, url_for, Response
from werkzeug import secure_filename
from slugify import slugify
from fablr.controller.resource import (ResourceHandler, ResourceRoutingStrategy, ResourceAccessPolicy,
    RacModelConverter, RacBaseForm, ResourceError, generate_flash)
from fablr.model.shop import Product, Order, OrderLine, OrderStatus, Address
from pdf import fingerprint_pdf
from flask.ext.mongoengine.wtf import model_form
from wtforms.fields import FormField, FieldList, HiddenField
from flask.ext.babel import lazy_gettext as _

logger = current_app.logger if current_app else logging.getLogger(__name__)

shop_app = Blueprint('shop', __name__, template_folder='../templates/shop')

stripe.api_key = current_app.config['STRIPE_SECRET_KEY']

product_access = ResourceAccessPolicy({
  'view':'user',
  '_default':'admin'
})

product_strategy = ResourceRoutingStrategy(Product, 'products', 'slug',
  short_url=False, form_class=model_form(Product, base_class=RacBaseForm,
  exclude=['slug'], converter=RacModelConverter()), access_policy=product_access)

class ProductHandler(ResourceHandler):
  def list(self, r):
    if not (g.user and g.user.admin):
      filter = r.get('filter',{})
      filter.update({'status__ne':'hidden'})
      print filter
      r['filter'] = filter
    return super(ProductHandler, self).list(r)

ProductHandler.register_urls(shop_app, product_strategy)

order_access = ResourceAccessPolicy({
  'my_orders':'user',
  'list':'admin',
  'edit':'private',
  'form_edit':'private',
  '_default':'admin'
})

order_strategy = ResourceRoutingStrategy(Order, 'orders', form_class=model_form(
  Order, base_class=RacBaseForm, only=['order_lines', 'shipping_address',
  'shipping_mobile'], converter=RacModelConverter()), access_policy=order_access)

# This injects the "cart_items" into templates in shop_app
@shop_app.context_processor
def inject_cart():
    cart_order = Order.objects(user=g.user, status=OrderStatus.cart).only('total_items').first()
    return dict(cart_items=cart_order.total_items if cart_order else 0)

# Order states and form
# cart.
# Only one order per user can be in this state at the same time.
# Product quantities and comments can be changed, new orderlines can be added or removed.
# Address will not be editable
# ordered
# Order has been confirmed and sent for payment. Quantities can no longer be changed.
# paid
# Order has been confirmed paid. Address and comments can be changed, but with warning (as it may be too late for shipment)
# shipped
# Order has been shipped and is impossible to edit.
# error
# an error needing manual review. includes requests for refund, etc.


CartOrderLineForm = model_form(OrderLine, only=['quantity','comment'], base_class=RacBaseForm, converter=RacModelConverter())
# Orderlines that only include comments, to allow for editing comments but not the order lines as such
LimitedOrderLineForm = model_form(OrderLine, only=['comment'], base_class=RacBaseForm, converter=RacModelConverter())
ShippingForm = model_form(Address, base_class=RacBaseForm, converter=RacModelConverter())

class CartForm(RacBaseForm):
  order_lines = FieldList(FormField(CartOrderLineForm))
  shipping_address = FormField(ShippingForm)
  stripe_token = HiddenField()

class PostCartForm(RacBaseForm):
  order_lines = FieldList(FormField(LimitedOrderLineForm))
  shipping_address = FormField(ShippingForm)

class OrderHandler(ResourceHandler):

  # We have to tailor our own edit because the form needs to be conditionally
  # modified
  def edit(self, r):
    item = r['item']
    auth = self.strategy.authorize(r['op'], item)
    r['auth'] = auth
    if not auth:
      raise ResourceError(auth.error_code, r=r, message=auth.message)
    r['template'] = self.strategy.item_template()
    if item.status=='cart':
      Formclass = CartForm
    else:
      Formclass = PostCartForm
    form = Formclass(request.form, obj=item)
    raise Exception()
    # logger.warning('Form %s validates to %s' % (request.form, form.validate()))
    if not form.validate():
      r['form'] = form
      raise ResourceError(400, r=r)
    if not isinstance(form, RacBaseForm):
      raise ValueError("Edit op requires a form that supports populate_obj(obj, fields_to_populate)")
    # We now have a validated form. Let's save the order first, then attempt to purchase it.
# This is very important, as the save() will re-calculate key values for this order
    form.populate_obj(item, request.form.keys())
    item.save()

    if form.stripe_token.data: # We have token data, so this is a purchase
      try:
        charge = stripe.Charge.create(
          source=form.stripe_token.data,
          amount=int(item.total_price*100), # Stripe takes input in "cents" or similar
          currency=item.currency,
          description=unicode(item),
          metadata={'order_id': item.id}
        )
        if charge['status'] == 'succeeded':
          item.status = OrderStatus.paid
          item.charge_id = charge['id']
          item.save()
      except stripe.error.CardError, e:
        pass


    # In case slug has changed, query the new value before redirecting!
    r['next'] = url_for('.order_form_edit', order=r['item'].id)

    logger.info("Edit on %s/%s", self.strategy.resource_name, item[self.strategy.id_field])
    generate_flash("Edited",self.strategy.resource_name,item)
    return r

  def my_orders(self, r):
    filter = r.get('filter',{})
    filter.update({'user':g.user})
    r['filter'] = filter
    return super(OrderHandler, self).list(r)

  # Endpoint will be 'order_cart' as it's attached to OrderHandler
  @ResourceHandler.methods(['GET','POST'])
  def cart(self, r):
    r['template'] = 'shop/order_item.html'

    if g.user:
      cart_order = Order.objects(user=g.user, status=OrderStatus.cart).first()
      if not cart_order:
        cart_order = Order(user=g.user, email=g.user.email).save()
      r['item'] = cart_order
      r['order'] = cart_order
      r['url_args'] = {'order':cart_order.id}
      r['stripe_key'] = current_app.config['STRIPE_PUBLIC_KEY']
    else:
      raise ResourceError(401, _('Need to log in to use shopping cart'))
    if request.method == 'GET':
      self.form_class = CartForm
      r = self.form_edit(r)

    elif request.method == 'POST':
      if request.form.has_key('product'):
        slug = request.form.get('product')
        p = Product.objects(slug=slug).first()
        if p:
          found = False
          for ol in cart_order.order_lines:
            if ol.product == p:
              ol.quantity += 1
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

    return r

OrderHandler.register_urls(shop_app, order_strategy)

@shop_app.route('/')
def index():
    product_families = Product.objects().distinct('family')
    return render_template('shop/_page.html', product_families=product_families)

### POST cart - add products, create order if needed
### GET cart - current order, displayed differently depending on current state

### my orders
@current_app.template_filter('currency')
def currency(value):
  return ("{:.0f}" if float(value).is_integer() else "{:.2f}").format(value)
