
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from builtins import str
from past.utils import old_div
from datetime import datetime, timedelta, date

from flask import g
from flask import request
from flask_babel import lazy_gettext as _, gettext
from .misc import Document, datetime_month_options  # Enhanced document
from mongoengine import (EmbeddedDocument, StringField, DateTimeField, FloatField,
                         ReferenceField, BooleanField, ListField, IntField, EmailField, EmbeddedDocumentField, MapField, NULLIFY, DENY, CASCADE)
from mongoengine.errors import ValidationError

from .asset import FileAsset
from .misc import slugify, Choices, Address, reference_options, choice_options, numerical_options, datetime_delta_options, \
    from7to365
from .user import User
from .world import Publisher, World

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

# TODO replace small letters for currency keys to large, to match babel and common use
Currencies = Choices(
    eur='EUR',
    sek='SEK'
)

FX_FORMAT ={
    'eur': u'€ %s',
    'sek': u'%s :-'
}

FX_IN_SEK = {
    'eur': 9.0,
    'sek': 1.0
}

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
    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, required=True, verbose_name=_('Publisher'))
    world = ReferenceField(World, reverse_delete_rule=DENY, verbose_name=_('World'))
    family = StringField(max_length=60, verbose_name=_('Product Family'))
    created = DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
    updated = DateTimeField(default=datetime.utcnow, verbose_name=_('Updated'))
    type = StringField(choices=ProductTypes.to_tuples(), required=True, verbose_name=_('Type'))
    # TODO should be required=True, but that currently maps to Required, not InputRequired validator
    # Required will check the value and 0 is determined as false, which blocks prices for 0
    price = FloatField(min_value=0, default=0, required=True, verbose_name=_('Price'))
    tax = FloatField(min_value=0, default=0.25, choices=[(0.25, '25%'), (0.06, '6%'), (0, '0% (Auto)')], verbose_name=_('Tax'))
    currency = StringField(required=True, choices=Currencies.to_tuples(), default=Currencies.sek,
                           verbose_name=_('Currency'))
    status = StringField(choices=ProductStatus.to_tuples(), default=ProductStatus.hidden, verbose_name=_('Status'))
    # TODO DEPRECATE in DB version 3
    feature_image = ReferenceField(FileAsset, reverse_delete_rule=NULLIFY, verbose_name=_('Feature Image'))
    images = ListField(ReferenceField(FileAsset, reverse_delete_rule=NULLIFY), verbose_name=_('Product Images'))
    acknowledgement = BooleanField(default=False, verbose_name=_('Name in book'))
    comment_instruction = StringField(max_length=20, verbose_name=_('Instructions for comments in order'))
    # Deny removal of downloadable files as people will lose access
    downloadable_files = ListField(ReferenceField(FileAsset, reverse_delete_rule=DENY), verbose_name=_('Downloadable files'))

    # Executes before saving
    def clean(self):
        self.updated = datetime.utcnow()
        if request.values.get('downloadable_files', None) is None:
            self.downloadable_files = []
        self.slug = slugify(self.title)

    @property  # For convenience
    def get_feature_image(self):
        return self.images[0] if self.images else None

    def in_orders(self):
        # This raw query finds orders where at least on order_line includes this product
        q = Order.objects(__raw__={'order_lines': {'$elemMatch': {'product': self.id}}})
        return q

    def delete(self):
        if self.in_orders().count() > 0:
            raise ValidationError("Cannot delete product %r as it's referenced by Orders" % self)
        super(Product, self).delete()

    def __str__(self):
        return u'%s %s %s' % (self.title, gettext('by'), self.publisher)

    def is_owned_by_current_user(self):
        return g.user and (g.user.admin or self in products_owned_by_user(g.user))

    # TODO hack to avoid bug in https://github.com/MongoEngine/mongoengine/issues/1279
    def get_field_display(self, field):
        return self._BaseDocument__get_field_display(self._fields[field])


Product.world.filter_options = reference_options('world', Product)
Product.type.filter_options = choice_options('type', Product.type.choices)
Product.price.filter_options = numerical_options('price', [0, 50, 100, 200])
Product.created.filter_options = datetime_delta_options('created', from7to365)


class OrderLine(EmbeddedDocument):
    quantity = IntField(min_value=1, default=1, verbose_name=_('Comment'))
    product = ReferenceField(Product, required=True, verbose_name=_('Product'))
    price = FloatField(min_value=0, required=True, verbose_name=_('Price'))
    comment = StringField(max_length=99, verbose_name=_('Comment'))

    def __str__(self):
        return u'%ix %s @ %s (%s)' % (self.quantity, self.product, self.price, self.comment)


OrderStatus = Choices(
    cart=_('Cart'),
    checkout=_('Checkout'),
    ordered=_('Ordered'),
    paid=_('Paid'),
    shipped=_('Shipped'),
    error=_('Error'))


class Stock(Document):
    """This is a special document which holds all stock status for a publisher's products.
    It is kept as a single document, to ensure that we can do single document atomic updates
    using mongodb, without too much trouble. E.g. we can update the stock status of a full OrderList
    with one command and one lock.
    """
    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, unique=True, verbose_name=_('Publisher'))
    updated = DateTimeField(default=datetime.utcnow, verbose_name=_('Updated'))
    stock_count = MapField(field=IntField(min_value=-1, default=0))

    def clean(self):
        self.updated = datetime.utcnow()

    def display_stock(self, product):
        if product in self.stock_count:
            if self.stock_count[product] <0:
                return _("Unlimited stock")
            if self.stock_count[product] == 0:
                return _("No stock")
            elif 0 < self.stock_count[product] < 5:
                return _("A few items")
            else:
                return _("Many items")
        else:
           return _("Unknown")


class Order(Document):
    user = ReferenceField(User, reverse_delete_rule=DENY, verbose_name=_('User'))
    session = StringField(verbose_name=_('Session ID'))
    email = EmailField(max_length=60, verbose_name=_('Email'))
    order_lines = ListField(EmbeddedDocumentField(OrderLine))
    total_items = IntField(min_value=0, default=0, verbose_name=_('# items'))  # Total number of items
    total_price = FloatField(min_value=0, default=0.0,
                             verbose_name=_('Total price'))  # Total price of order incl shipping
    total_tax = FloatField(min_value=0, default=0.0, verbose_name=_('Total tax'))  # Total tax of order
    currency = StringField(choices=Currencies.to_tuples(), verbose_name=_('Currency'))
    created = DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
    updated = DateTimeField(default=datetime.utcnow, verbose_name=_('Updated'))
    status = StringField(choices=OrderStatus.to_tuples(), default=OrderStatus.cart, verbose_name=_('Status'))
    shipping = ReferenceField(Product, reverse_delete_rule=DENY, verbose_name=_('Shipping'))
    charge_id = StringField()  # Stores the Stripe charge id
    internal_comment = StringField(verbose_name=_('Internal Comment'))
    shipping_address = EmbeddedDocumentField(Address)

    def __str__(self):
        max_prod, max_price = None, -1
        for ol in self.order_lines:
            if ol.price > max_price:
                max_prod, max_price = ol.product, ol.price
        if max_prod:
            additional_items = self.total_items-1
            s = u'%s%s' % (
                max_prod.title,
                ' ' + _('and %(additional_items)s more', additional_items=additional_items) if additional_items else '')
            # s += u' [%s]' % self.total_price_display()
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

    def total_price_sek(self):
        """Returns total price as an int in SEK equivalent based on pre-defined FX rate"""
        return int(self.total_price*FX_IN_SEK[self.currency])

    def total_price_display(self):
        price_format = (u'{:.0f}' if float(self.total_price).is_integer() else u'{:.2f}').format(self.total_price)
        fx_format = FX_FORMAT.get(self.currency, u'%s')
        return fx_format % price_format

    def update_stock(self, publisher, update_op, select_op=None):
        """Updates the stock count (either by inc(rement) or dec(rement) operators) and optionally ensures a select
        query first goes through, e.g. "gte 5". Is an atomic operation."""
        stock = Stock.objects(publisher=publisher).first()
        if stock:
            order_dict = {}
            for ol in self.order_lines:
                # Only pick products that are supposed to be available in stock (digital is a different flag)
                if ol.product.status == ProductStatus.available:
                    order_dict[ol.product.slug] = order_dict.get(ol.product.slug, 0) + ol.quantity
            select_args = {}
            update_args = {}
            for prod, quantity in order_dict.items():
                if select_op:  # We only need to do this check when reducing quantity
                    select_args['stock_count__%s__%s' % (prod, select_op)] = quantity
                update_args['%s__stock_count__%s' % (update_op, prod)] = quantity
            if select_args and update_args:
                # Makes an atomic update
                allowed = stock.modify(query=select_args, **update_args)
                print(select_args, update_args, "was allowed? %s" % allowed)
                return allowed
            else:
                return True  # If nothing to update, approve it
        else:
            raise ValueError("No stock status available for publisher %s" % publisher)

    def deduct_stock(self, publisher):
        return self.update_stock(publisher, 'dec', 'gte')

    def return_stock(self, publisher):
        return self.update_stock(publisher, 'inc')

    # Executes before saving
    def clean(self):
        self.updated = datetime.utcnow()
        num, sum, tax = 0, 0.0, 0.0
        for ol in self.order_lines:
            if self.currency:
                if ol.product.currency != self.currency:
                    raise ValidationError(
                        u'This order is in %s, cannot add line with %s' % (self.currency, ol.product.currency))
            else:
                self.currency = ol.product.currency
            if ol.product.status == ProductStatus.out_of_stock:
                raise ValidationError(u'Product %s is out of stock' % ol.product)

            num += ol.quantity
            sum += ol.quantity * ol.price
            # Tax rates are given as e.g. 25% or 0.25. The taxable part of sum is
            # sum * (taxrate / (taxrate+1))
            tax += ol.quantity * ol.price * (old_div(ol.product.tax, (ol.product.tax + 1.0)))
        if sum > 0:
            if self.shipping:
                if self.shipping.tax == 0:  # This means set tax of shipping as the average tax of all products in order
                    tax_rate = old_div(tax, sum)
                    tax += self.shipping.price * (old_div(tax_rate, (tax_rate + 1.0)))
                else:
                    tax += self.shipping.price * (old_div(self.shipping.tax, (self.shipping.tax + 1.0)))
                sum += self.shipping.price  # Do after we calculate average tax above
        else:
            self.currency = None  # Clear it to avoid errors adding different product currencies back again

        self.total_items = num
        self.total_price = sum
        self.total_tax = tax
        if self.user and not self.email:
            self.email = self.user.email


Order.total_items.filter_options = numerical_options('total_items', [0, 1, 3, 5])
Order.total_price.filter_options = numerical_options('total_price', [0, 50, 100, 200])
Order.status.filter_options = choice_options('status', Order.status.choices)
Order.created.filter_options = datetime_month_options('created')
Order.updated.filter_options = datetime_delta_options('updated',
                                                      [timedelta(days=1),
                                                 timedelta(days=7),
                                                 timedelta(days=30),
                                                 timedelta(days=90),
                                                 timedelta(days=365)])


def products_owned_by_user(user):
    orders = Order.objects(user=user, status__in=[OrderStatus.paid, OrderStatus.shipped])
    return [order_line.product for order_line in [order_line for order in orders for order_line in order.order_lines]]
