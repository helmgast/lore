from datetime import datetime, timedelta, date

from flask import g
from flask import request
from flask.ext.babel import lazy_gettext as _
from flask.ext.mongoengine import Document  # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, DateTimeField, FloatField,
                         ReferenceField, BooleanField, ListField, IntField, EmailField, EmbeddedDocumentField)
from mongoengine.errors import ValidationError

from asset import FileAsset
from misc import slugify, Choices, Address, reference_options, choice_options, numerical_options, datetime_options, \
    from7to365
from user import User
from world import ImageAsset, Publisher, World

ProductTypes = Choices(
    book=_('Book'),
    item=_('Item'),
    digital=_('Digital'),
    shipping=_('Shipping fee'))

ProductStatus = Choices(
    pre_order=_('Pre-order'),
    available=_('Available'),
    ready_for_download=_('Ready for download'),
    out_of_stock=_('Out of stock'),
    hidden=_('Hidden'))

Currencies = Choices(
    eur='EUR',
    sek='SEK'
)


# Product number logic
# PB-PF-nnnn-x
# PB = publisher code
# PF = product family, e.g. J(arn), E(eon)
# nnnn = article number
# x = variant code (can be anything)

# Shipping product numbers
# PB-S-type-country
# PB = publisher code
# S = shipping
# type = one of ProductTypes except shipping
# country = 2-letter country code

class Product(Document):
    slug = StringField(unique=True, max_length=62)  # URL-friendly name
    product_number = StringField(max_length=10, sparse=True, verbose_name=_('Product Number'))
    project_code = StringField(max_length=10, sparse=True, verbose_name=_('Project Code'))
    title = StringField(max_length=60, required=True, verbose_name=_('Title'))
    description = StringField(max_length=500, verbose_name=_('Description'))
    publisher = ReferenceField(Publisher, required=True, verbose_name=_('Publisher'))
    world = ReferenceField(World, verbose_name=_('World'))
    family = StringField(max_length=60, verbose_name=_('Product Family'))
    created = DateTimeField(default=datetime.utcnow(), verbose_name=_('Created'))
    type = StringField(choices=ProductTypes.to_tuples(), required=True, verbose_name=_('Type'))
    # TODO should be required=True, but that currently maps to Required, not InputRequired validator
    # Required will check the value and 0 is determined as false, which blocks prices for 0
    price = FloatField(min_value=0, default=0, verbose_name=_('Price'))
    tax = FloatField(min_value=0, default=0.25, choices=[(0.25, '25%'), (0.06, '6%'), (0, '0% (Auto)')], verbose_name=_('Tax'))
    currency = StringField(required=True, choices=Currencies.to_tuples(), default=Currencies.sek,
                           verbose_name=_('Currency'))
    status = StringField(choices=ProductStatus.to_tuples(), default=ProductStatus.hidden, verbose_name=_('Status'))
    feature_image = ReferenceField(ImageAsset, verbose_name=_('Feature Image'))
    acknowledgement = BooleanField(default=False, verbose_name=_('Name in book'))
    comment_instruction = StringField(max_length=20, verbose_name=_('Instructions for comments in order'))
    downloadable_files = ListField(ReferenceField(FileAsset), verbose_name=_('Downloadable files'))

    # Executes before saving
    def clean(self):
        if request.values.get('downloadable_files', None) is None:
            self.downloadable_files = []
        self.slug = slugify(self.title)

    def in_orders(self):
        # This raw query finds orders where at least on order_line includes this product
        q = Order.objects(__raw__={'order_lines': {'$elemMatch': {'product': self.id}}})
        return q

    def delete(self):
        if self.in_orders().count() > 0:
            raise ValidationError("Cannot delete product %r as it's referenced by Orders" % self)
        super(Product, self).delete()

    def __unicode__(self):
        return u'%s %s %s' % (self.title, _('by'), self.publisher)

    def is_owned_by_current_user(self):
        return g.user and (g.user.admin or self in products_owned_by_user(g.user))

    # TODO hack to avoid bug in https://github.com/MongoEngine/mongoengine/issues/1279
    def get_field_display(self, field):
        return self._BaseDocument__get_field_display(self._fields[field])


Product.world.filter_options = reference_options('world', Product)
Product.type.filter_options = choice_options('type', Product.type.choices)
Product.price.filter_options = numerical_options('price', [0, 50, 100, 200])
Product.created.filter_options = datetime_options('created', from7to365)


class OrderLine(EmbeddedDocument):
    quantity = IntField(min_value=1, default=1, verbose_name=_('Comment'))
    product = ReferenceField(Product, required=True, verbose_name=_('Product'))
    price = FloatField(min_value=0, required=True, verbose_name=_('Price'))
    comment = StringField(max_length=99, verbose_name=_('Comment'))

    def __unicode__(self):
        return u'%ix %s @ %s (%s)' % (self.quantity, self.product, self.price, self.comment)


OrderStatus = Choices(
    cart=_('Cart'),
    checkout=_('Checkout'),
    ordered=_('Ordered'),
    paid=_('Paid'),
    shipped=_('Shipped'),
    error=_('Error'))


class Order(Document):
    user = ReferenceField(User, verbose_name=_('User'))
    session = StringField(verbose_name=_('Session ID'))
    email = EmailField(max_length=60, verbose_name=_('Email'))
    order_lines = ListField(EmbeddedDocumentField(OrderLine))
    total_items = IntField(min_value=0, default=0, verbose_name=_('# items'))  # Total number of items
    total_price = FloatField(min_value=0, default=0.0,
                             verbose_name=_('Total price'))  # Total price of order incl shipping
    total_tax = FloatField(min_value=0, default=0.0, verbose_name=_('Total tax'))  # Total tax of order
    currency = StringField(choices=Currencies.to_tuples(), verbose_name=_('Currency'))
    created = DateTimeField(default=datetime.utcnow(), verbose_name=_('Created'))
    updated = DateTimeField(default=datetime.utcnow(), verbose_name=_('Updated'))
    status = StringField(choices=OrderStatus.to_tuples(), default=OrderStatus.cart, verbose_name=_('Status'))
    shipping = ReferenceField(Product, verbose_name=_('Shipping'))
    charge_id = StringField()  # Stores the Stripe charge id
    internal_comment = StringField(verbose_name=_('Internal Comment'))
    shipping_address = EmbeddedDocumentField(Address)

    def __str__(self):
        s = unicode(self).encode('utf-8')
        return s

    def __unicode__(self):
        max_prod, max_price = None, -1
        for ol in self.order_lines:
            if ol.price > max_price:
                max_prod, max_price = ol.product, ol.price
        if max_prod:
            s = u'%s%s' % (
                max_prod.title,
                ' ' + _('and %(total_items)s more', total_items=self.total_items) if len(self.order_lines) > 1 else '')
        else:
            s = u'%s' % _('Empty order')
        return s

    # TODO hack to avoid bug in https://github.com/MongoEngine/mongoengine/issues/1279
    def get_field_display(self, field):
        return self._BaseDocument__get_field_display(self._fields[field])

    def is_paid_or_shipped(self):
        return self.status in [OrderStatus.paid, OrderStatus.shipped]

    def is_digital(self):
        """True if this order only contains products of type Digital"""
        for ol in self.order_lines:
            if ol.product.type != ProductTypes.digital:
                return False
        return len(self.order_lines) > 0  # True if there was lines in order, false if not

    def total_price_int(self):
        """Returns total price as an int, suitable for Stripe"""
        return int(self.total_price * 100)

    # Executes before saving
    def clean(self):
        self.updated = datetime.utcnow()
        num, sum, tax = 0, 0.0, 0.0
        for ol in self.order_lines:
            if self.currency:
                if ol.product.currency != self.currency:
                    raise ValidationError(
                        'This order is in %s, cannot add line with %s' % (self.currency, ol.product.currency))
            else:
                self.currency = ol.product.currency
            num += ol.quantity
            sum += ol.quantity * ol.price
            # Tax rates are given as e.g. 25% or 0.25. The taxable part of sum is
            # sum * (taxrate / (taxrate+1))
            tax += ol.quantity * ol.price * (ol.product.tax / (ol.product.tax + 1))

        if self.shipping:
            if self.shipping.tax == 0:  # This means set tax of shipping as the average tax of all products in order
                tax_rate = tax/sum
                tax += self.shipping.price * (tax_rate / (tax_rate + 1))
            else:
                tax += self.shipping.price * (self.shipping.tax / (self.shipping.tax + 1))
            sum += self.shipping.price  # Do after we calculate average tax above

        self.total_items = num
        self.total_price = sum
        self.total_tax = tax
        if self.user and not self.email:
            self.email = self.user.email


Order.total_items.filter_options = numerical_options('total_items', [0, 1, 3, 5])
Order.total_price.filter_options = numerical_options('total_price', [0, 50, 100, 200])
Order.status.filter_options = choice_options('status', Order.status.choices)
Order.updated.filter_options = datetime_options('updated',
                                                [timedelta(days=1),
                                                 timedelta(days=7),
                                                 timedelta(days=30),
                                                 timedelta(days=90),
                                                 timedelta(days=365)])


def products_owned_by_user(user):
    orders = Order.objects(user=user, status__in=[OrderStatus.paid, OrderStatus.shipped])
    return map(lambda order_line: order_line.product,
               [order_line for order in orders for order_line in order.order_lines])
