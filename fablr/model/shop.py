import mimetypes
import re
from flask import g
from fablr.model.asset import FileAsset
from fablr.app import db
from fablr.model.misc import list_to_choices
from flask.ext.babel import lazy_gettext as _
from mongoengine.errors import ValidationError
from datetime import datetime
from user import User
from slugify import slugify
from misc import Choices
from world import ImageAsset
from flask import request

ProductTypes = Choices(
  book=_('Book'),
  item=_('Item'),
  digital=_('Digital'),
  shipping=_('Shipping fee'))

ProductStatus = Choices(
  pre_order = _('Pre-order'),
  available = _('Available'),
  ready_for_download = _('Ready for download'),
  out_of_stock = _('Out of stock'),
  hidden = _('Hidden'))

Currencies = Choices(
  eur = 'EUR',
  sek = 'SEK'
  )

class Product(db.Document):
  slug = db.StringField(unique=True, max_length=62) # URL-friendly name
  product_no = db.StringField(unique=True, max_length=10, sparse=True)
  title = db.StringField(max_length=60, required=True, verbose_name=_('Title'))
  description = db.StringField(max_length=500, verbose_name=_('Description'))
  publisher = db.StringField(max_length=60, required=True, verbose_name=_('Publisher'))
  family = db.StringField(max_length=60, verbose_name=_('Product Family'))
  created = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
  type = db.StringField(choices=ProductTypes.to_tuples(), required=True, verbose_name=_('Type'))
  # should be required=True, but that currently maps to Required, not InputRequired validator
  # Required will check the value and 0 is determined as false, which blocks prices for 0
  price = db.FloatField(min_value=0, default=0, verbose_name=_('Price'))
  tax = db.FloatField(min_value=0, default=0, verbose_name=_('Tax'))
  currency = db.StringField(required=True, choices=Currencies.to_tuples(), default=Currencies.sek, verbose_name=_('Currency'))
  status = db.StringField(choices=ProductStatus.to_tuples(), default=ProductStatus.hidden, verbose_name=_('Status'))
  # Names of resources (downloadable files)
  # TODO: Remove once downloadable_files has been migrated
  resources = db.ListField(db.StringField())
  group = db.StringField(max_length=60, verbose_name=_('Product Group'))
  feature_image = db.ReferenceField(ImageAsset, verbose_name=_('Feature Image'))
  acknowledgement = db.BooleanField(default=False, verbose_name=_('Name in book'))
  downloadable_files = db.ListField(db.ReferenceField(FileAsset), verbose_name=_('Downloadable files'))

  # Executes before saving
  def clean(self):
    if request.values.get('downloadable_files', None) is None:
      self.downloadable_files = []
    self.slug = slugify(self.title)

  def __unicode__(self):
    return u'%s %s %s' % (self.title, _('by'), self.publisher)

  def is_owned_by_current_user(self):
    return g.user and (g.user.admin or self in products_owned_by_user(g.user))

class OrderLine(db.EmbeddedDocument):
  quantity = db.IntField(min_value=1, default=1, verbose_name=_('Comment'))
  product = db.ReferenceField(Product, required=True, verbose_name=_('Product'))
  price = db.FloatField(min_value=0, required=True, verbose_name=_('Price'))
  comment = db.StringField(max_length=99, verbose_name=_('Comment'))

class Address(db.EmbeddedDocument):
  name = db.StringField(max_length=60, verbose_name=_('Name'))
  street = db.StringField(max_length=60, verbose_name=_('Street'))
  zipcode = db.StringField(max_length=8, verbose_name=_('ZIP Code'))
  city = db.StringField(max_length=60, verbose_name=_('City'))
  country = db.StringField(max_length=60, verbose_name=_('Country'))
  mobile = db.StringField(min_length=8, max_length=14, verbose_name=_('Cellphone Number'))

OrderStatus = Choices(
  cart = _('Cart'),
  ordered = _('Ordered'),
  paid = _('Paid'),
  shipped = _('Shipped'),
  error = _('Error'))

class Order(db.Document):
  user = db.ReferenceField(User, verbose_name=_('User'))
  session = db.StringField(verbose_name=_('Session ID'))
  email = db.EmailField(max_length=60, required=True, verbose_name=_('Email'))
  order_lines = db.ListField(db.EmbeddedDocumentField(OrderLine))
  total_items = db.IntField(min_value=0, default=0) # Total number of items
  total_price = db.FloatField(min_value=0, default=0.0, verbose_name=_('Total price')) # Total price of order
  currency = db.StringField(choices=Currencies.to_tuples(), verbose_name=_('Currency'))
  created = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
  updated = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Updated'))
  status = db.StringField(choices=OrderStatus.to_tuples(), default=OrderStatus.cart, verbose_name=_('Status'))
  charge_id = db.StringField() # Stores the Stripe charge id
  shipping_address = db.EmbeddedDocumentField(Address)

  def __unicode__(self):
    max_prod, max_price = None, -1
    for ol in self.order_lines:
      if ol.price > max_price:
        max_prod, max_price = ol.product, ol.price
    if max_prod:
      s = u'%s%s' % (
        max_prod.title,
        ' '+_('and %(total_items)s more', total_items=self.total_items) if len(self.order_lines)>1 else '')
    else:
      s = u'%s' % _('Empty order')
    return s

  def is_paid_or_shipped(self):
    return self.status in [OrderStatus.paid, OrderStatus.shipped]

  # Executes before saving
  def clean(self):
    self.updated = datetime.utcnow
    num, sum =0, 0.0
    for ol in self.order_lines:
      if self.currency:
        if ol.product.currency != self.currency:
          raise ValidationError('This order is in %s, cannot add line with %s' % (self.currency, ol.product.currency))
      else:
        self.currency = ol.product.currency
      num += ol.quantity
      sum += ol.quantity * ol.price
    self.total_items = num
    self.total_price = sum

def products_owned_by_user(user):
    orders = Order.objects(user=user, status__in=[OrderStatus.paid, OrderStatus.shipped])
    return map(lambda order_line: order_line.product, [order_line for order in orders for order_line in order.order_lines])
