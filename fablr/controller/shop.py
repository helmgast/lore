"""
  controller.shop
  ~~~~~~~~~~~~~~~~

  This is the controller and Flask blueprint for a basic webshopg. It will
  setup the URL routes based on Resource and provide a checkout flow. It
  also hosts important return URLs for the payment processor.

  :copyright: (c) 2014 by Helmgast AB
"""
import logging
from itertools import izip

import stripe
from flask import Blueprint, current_app, g, request, url_for, redirect, abort, session, flash, Markup
from flask.ext.babel import lazy_gettext as _
from flask.ext.classy import route
from flask.ext.mongoengine.wtf import model_form
from mongoengine import NotUniqueError, ValidationError
from wtforms.fields import FormField, FieldList, StringField
from wtforms.fields.html5 import EmailField
from wtforms.utils import unset_value
from wtforms.validators import InputRequired, Email

from fablr.controller.mailer import send_mail
from fablr.controller.resource import (ResourceRoutingStrategy, ResourceAccessPolicy,
                                       RacModelConverter, RacBaseForm, ResourceView,
                                       filterable_fields_parser, prefillable_fields_parser, ListResponse, ItemResponse,
                                       Authorization)
from fablr.controller.world import set_theme
from fablr.model.shop import Product, Order, OrderLine, Address, OrderStatus
from fablr.model.user import User
from fablr.model.world import Publisher

logger = current_app.logger if current_app else logging.getLogger(__name__)

shop_app = Blueprint('shop', __name__, template_folder='../templates/shop')

stripe.api_key = current_app.config['STRIPE_SECRET_KEY']


class ProductsView(ResourceView):
    subdomain = '<publisher>'
    access_policy = ResourceAccessPolicy({
        'view': 'public',
        'list': 'public',
        '_default': 'admin'
    })
    model = Product
    list_template = 'shop/product_list.html'
    list_arg_parser = filterable_fields_parser(['title', 'description', 'created', 'type', 'world', 'price'])
    item_template = 'shop/product_item.html'
    item_arg_parser = prefillable_fields_parser(['title', 'description', 'created', 'type', 'world', 'price'])
    form_class = model_form(Product,
                            base_class=RacBaseForm,
                            exclude=['slug'],
                            converter=RacModelConverter())

    # fields to order_by,(order_by key, e.g. order by id, by slug, etc?)
    # no point ordering for reference fields, and translated choice fields will be wrong order as well

    # fields to filter by
    # DateTimeField - certain time spans: today, last week, last month, last year, >1 year.
    #   Choices cannot be combined.
    # Choice-fields: filter by the choices available
    #   Choices can be combined.
    # Numeric fields (int, Float): e.g. 0-5,5-20,20-100, 100-200
    #   Cannot be combined.
    # ReferenceFields: a select box to filter by one or many choices, or a few options if less than <6
    #   Choices can be combined.
    # StringField: no filtering
    # Boolean: Filter yes or no
    # ListField: no filtering (could have "has members" or "not has members")
    # filterable_fields = ['name', 'name2'], looked up at r.model._fields[name]
    # field_options = {
    #   'world': [
    #       (url, active, name),
    #       {'world'},
    #       {'noir'}],
    #   'price': [
    #       {'price':0, 'price__lt':5}
    #   ]

    def index(self, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        products = Product.objects(status__ne='hidden').order_by('type', '-price')
        r = ListResponse(ProductsView, [('products', products), ('publisher', publisher)])
        r.auth_or_abort()
        r.prepare_query()
        set_theme(r, 'publisher', publisher.slug)

        return r

    def get(self, id, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        if id == 'post':
            r = ItemResponse(ProductsView, [('product', None), ('publisher', publisher)], extra_args={'intent': 'post'})
        else:
            product = Product.objects(slug=id).first_or_404()
            r = ItemResponse(ProductsView, [('product', product), ('publisher', publisher)])
        r.auth_or_abort()
        set_theme(r, 'publisher', publisher.slug)
        return r

    def post(self, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        r = ItemResponse(ProductsView, [('product', None), ('publisher', publisher)], method='post')
        product = Product()
        set_theme(r, 'publisher', publisher.slug)
        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(product)
        try:
            r.commit(new_instance=product)
        except (NotUniqueError, ValidationError) as err:
            flash(err.message, 'danger')
            return r, 400  # Respond with same page, including errors highlighted
        return redirect(r.args['next'] or url_for('shop.ProductsView:get', publisher=publisher.slug, id=product.slug))

    def patch(self, id, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        product = Product.objects(slug=id).first_or_404()
        r = ItemResponse(ProductsView, [('product', product), ('publisher', publisher)], method='patch')
        r.auth_or_abort()
        set_theme(r, 'publisher', publisher.slug)
        if not isinstance(r.form, RacBaseForm):
            raise ValueError("Edit op requires a form that supports populate_obj(obj, fields_to_populate)")
        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(product, request.form.keys())  # only populate selected keys
        r.commit()
        return redirect(r.args['next'] or url_for('shop.ProductsView:get', publisher=publisher.slug, id=product.slug))

    def delete(self, id, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        product = Product.objects(slug=id).first_or_404()
        r = ItemResponse(ProductsView, [('product', product), ('publisher', publisher)], method='delete')
        r.auth_or_abort()
        set_theme(r, 'publisher', publisher.slug)
        r.commit()
        return redirect(r.args['next'] or url_for('shop.ProductsView:index', publisher=publisher.slug))


ProductsView.register_with_access(shop_app, 'product')

CartOrderLineForm = model_form(OrderLine, only=['quantity'], base_class=RacBaseForm, converter=RacModelConverter())
# Orderlines that only include comments, to allow for editing comments but not the order lines as such
LimitedOrderLineForm = model_form(OrderLine, only=['comment'], base_class=RacBaseForm, converter=RacModelConverter())
AddressForm = model_form(Address, base_class=RacBaseForm, converter=RacModelConverter())


class FixedFieldList(FieldList):
    # TODO
    # Below is a very hacky approach to handle updating the order_list. When we send in a form
    # with a deleted row, it never appears in formdata. For example, we have a order_list of 2 items,
    # when the first is deleted only the second is submitted. Below code uses the indices of the
    # field ids, e.g. order_lines-0 and order_lines-1 to identify what was removed, and then
    # process and populate the right item from the OrderList field of the model.
    # This should be fixed by wtforms!

    def process(self, formdata, data=unset_value):
        print 'FieldList process formdata %s, data %s' % (formdata, data)
        self.entries = []
        if data is unset_value or not data:
            try:
                data = self.default()
            except TypeError:
                data = self.default

        self.object_data = data

        if formdata:
            indices = sorted(set(self._extract_indices(self.name, formdata)))
            if self.max_entries:
                indices = indices[:self.max_entries]

            for index in indices:
                try:
                    obj_data = data[index]
                    print "Got obj_data %s" % obj_data
                except LookupError:
                    obj_data = unset_value
                self._add_entry(formdata, obj_data, index=index)
                # if not indices:  # empty the list
                #     self.entries = []
        else:
            for obj_data in data:
                self._add_entry(formdata, obj_data)

        while len(self.entries) < self.min_entries:
            self._add_entry(formdata)

    def populate_obj(self, obj, name):
        old_values = getattr(obj, name, [])

        candidates = []
        indices = [e.id.rsplit('-', 1)[1] for e in self.entries]
        for i in indices:
            candidates.append(old_values[int(i)])

        _fake = type(str('_fake'), (object,), {})
        output = []
        for field, data in izip(self.entries, candidates):
            fake_obj = _fake()
            fake_obj.data = data
            field.populate_obj(fake_obj, 'data')
            output.append(fake_obj.data)

        setattr(obj, name, output)


class BuyForm(RacBaseForm):
    product = StringField(validators=[InputRequired(_("Please enter your email address."))])


class CartForm(RacBaseForm):
    order_lines = FixedFieldList(FormField(CartOrderLineForm))


class DetailsForm(RacBaseForm):
    shipping_address = FormField(AddressForm)
    email = EmailField("Email", validators=[
        InputRequired(_("Please enter your email address.")),
        Email(_("Please enter your email address."))])


class PaymentForm(RacBaseForm):
    order_lines = FixedFieldList(FormField(LimitedOrderLineForm))
    stripe_token = StringField(validators=[InputRequired(_("Please enter your email address."))])


class PostPaymentForm(RacBaseForm):
    order_lines = FixedFieldList(FormField(LimitedOrderLineForm))


class OrdersAccessPolicy(ResourceAccessPolicy):
    def is_owner(self, op, instance):
        if instance:
            if g.user == instance.user:
                return Authorization(True, _("Allowed access to %(instance)s as it's own order", instance=instance), privileged=True)
            else:
                return Authorization(False, _("Not allowed access to %(instance)s as not own order"))
        else:
            return Authorization(False, _("No instance to test for access on"))

class OrdersView(ResourceView):
    subdomain = '<publisher>'
    access_policy = OrdersAccessPolicy({
        'my_orders': 'user',
        'view': 'owner',
        'list': 'admin',
        'edit': 'admin',
        'form_edit': 'admin',
        '_default': 'admin'
    })
    model = Order
    list_template = 'shop/order_list.html'
    list_arg_parser = filterable_fields_parser(['id', 'user', 'created', 'updated', 'status', 'total_price', 'total_items'])
    item_template = 'shop/order_item.html'
    item_arg_parser = prefillable_fields_parser(['id', 'user', 'created', 'updated', 'status', 'total_price', 'total_items'])
    form_class = form_class = model_form(Order,
                                         base_class=RacBaseForm,
                                         only=['order_lines', 'shipping_address', 'shipping_mobile'],
                                         converter=RacModelConverter())

    def index(self, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        orders = Order.objects().order_by('-updated')  # last updated will show paid highest
        r = ListResponse(OrdersView, [('orders', orders), ('publisher', publisher)])
        r.auth_or_abort()
        r.prepare_query()
        set_theme(r, 'publisher', publisher.slug)
        return r

    def my_orders(self, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        orders = Order.objects(user=g.user).order_by('-updated')  # last updated will show paid highest
        r = ListResponse(OrdersView, [('orders', orders), ('publisher', publisher)], method='my_orders')
        r.auth_or_abort()
        r.prepare_query()
        set_theme(r, 'publisher', publisher.slug)
        return r

    def get(self, id, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        # TODO we dont support new order creation outside of cart yet
        # if id == 'post':
        #     r = ItemResponse(OrdersView, [('order', None), ('publisher', publisher)], extra_args={'intent': 'post'})
        order = Order.objects(id=id).first_or_404()
        r = ItemResponse(OrdersView, [('order', order), ('publisher', publisher)], form_class=PostPaymentForm)
        r.auth_or_abort()
        set_theme(r, 'publisher', publisher.slug)
        return r

    def patch(self, id, publisher):
        abort(501)  # Not implemented

    @route('/buy', methods=['PATCH'])
    def buy(self, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        cart_order = get_cart_order()
        r = ItemResponse(OrdersView, [('order', cart_order), ('publisher', publisher)], form_class=BuyForm,
                         method='patch')
        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        p = Product.objects(slug=r.form.product.data).first()
        if p:
            if not cart_order:
                # Create new cart-order and attach to session
                cart_order = Order(status='cart')  # status defaults to cart, but let's be explicit
                if g.user:
                    cart_order.user = g.user
                cart_order.save()  # Need to save to get an id
                session['cart_id'] = cart_order.id
                r.instance = cart_order  # set it in the response as well
            found = False
            for ol in cart_order.order_lines:
                if ol.product == p:
                    ol.quantity += 1
                    found = True
            if not found:  # create new orderline with this product
                new_ol = OrderLine(product=p, price=p.price)
                cart_order.order_lines.append(new_ol)
            cart_order.save()
            return r
        abort(400, 'Badly formed cart patch request')

    # Post means go to next step, patch means to stay
    @route('/cart', methods=['GET', 'PATCH', 'POST'])
    def cart(self, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        cart_order = get_cart_order()
        r = ItemResponse(OrdersView, [('order', cart_order), ('publisher', publisher)], form_class=CartForm,
                         extra_args={'view': 'cart', 'intent': 'post'})
        set_theme(r, 'publisher', publisher.slug)
        if request.method in ['PATCH', 'POST']:
            r.method = request.method.lower()
            if not r.validate():
                return r, 400  # Respond with same page, including errors highlighted
            r.form.populate_obj(cart_order)  # populate all of the object
            try:
                r.commit(flash=False)
            except ValidationError as ve:
                flash(ve.message, 'danger')
                return r, 400  # Respond with same page, including errors highlighted
            if request.method == 'PATCH':
                return redirect(r.args['next'] or url_for('shop.OrdersView:cart', **request.view_args))
            elif request.method == 'POST':
                return redirect(r.args['next'] or url_for('shop.OrdersView:details', **request.view_args))
        return r  # we got here if it's a get

    @route('/details', methods=['GET', 'POST'])
    def details(self, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        cart_order = get_cart_order()
        if not cart_order or cart_order.total_items < 1:
            return redirect(url_for('shop.OrdersView:cart', publisher=publisher.slug))

        r = ItemResponse(OrdersView, [('order', cart_order), ('publisher', publisher)], form_class=DetailsForm,
                         extra_args={'view': 'details', 'intent': 'post'})
        set_theme(r, 'publisher', publisher.slug)
        if request.method == 'POST':
            r.method = 'post'
            if not r.validate():
                return r, 400  # Respond with same page, including errors highlighted
            r.form.populate_obj(cart_order)  # populate all of the object
            if not g.user and User.objects(email=cart_order.email)[:1]:
                # An existing user has this email, force login or different email
                flash(Markup(_(
                    'Email belongs to existing user, please <a href="%(loginurl)s">login</a> first or change email',
                    loginurl=url_for('auth.login', next=request.url))),
                    'danger')
                return r, 400
            if not cart_order.is_digital():
                shipping_products = Product.objects(
                    publisher=publisher,
                    type='shipping',
                    currency=cart_order.currency,
                    description__contains=cart_order.shipping_address.country).order_by('-price')
                if shipping_products:
                    cart_order.shipping = shipping_products[0]
            try:
                r.commit(flash=False)
            except ValidationError as ve:
                flash(ve.message, 'danger')
                return r, 400  # Respond with same page, including errors highlighted
            return redirect(r.args['next'] or url_for('shop.OrdersView:pay', **request.view_args))
        return r  # we got here if it's a get

    @route('/pay', methods=['GET', 'POST'])
    def pay(self, publisher):
        publisher = Publisher.objects(slug=publisher).first_or_404()
        cart_order = get_cart_order()
        if not cart_order or not cart_order.shipping_address or not cart_order.user:
            return redirect(url_for('shop.OrdersView:cart', publisher=publisher.slug))
        r = ItemResponse(OrdersView, [('order', cart_order), ('publisher', publisher)], form_class=PaymentForm,
                         extra_args={'view': 'pay', 'intent': 'post'})
        set_theme(r, 'publisher', publisher.slug)
        r.stripe_key = current_app.config['STRIPE_PUBLIC_KEY']
        if request.method == 'POST':
            r.method = 'post'
            if not r.validate():
                return r, 400  # Respond with same page, including errors highlighted
            r.form.populate_obj(cart_order)  # populate all of the object
            try:
                charge = stripe.Charge.create(
                    source=r.form.stripe_token.data,
                    amount=cart_order.total_price_int(),  # Stripe takes input in "cents" or similar
                    currency=cart_order.currency,
                    description=unicode(cart_order),
                    metadata={'order_id': cart_order.id}
                )
                if charge['status'] == 'succeeded':
                    cart_order.status = OrderStatus.paid
                    cart_order.charge_id = charge['id']
            except stripe.error.CardError as e:
                abort(500, "Could not complete purchase: %s" % e.message, r=r)
            try:
                r.commit()
                send_mail([g.user.email], _('Thank you for your order!'), 'order', user=g.user, order=cart_order, publisher=publisher)
            except ValidationError as ve:
                flash(ve.message, 'danger')
                return r, 400  # Respond with same page, including errors highlighted
            return redirect(r.args['next'] or url_for('shop.OrdersView:get', id=cart_order.id, **request.view_args))
        return r  # we got here if it's a get


OrdersView.register_with_access(shop_app, 'order')



def get_cart_order():
    if session.get('cart_id', None):
        cart_order = Order.objects(id=session['cart_id']).first()
        if not cart_order or cart_order.status != 'cart' or (cart_order.user and cart_order.user != g.user):
            # Error, maybe someone is manipulating input, or we logged out and should clear the
            # association with that cart for safety
            # True if current user is different, or if current user is none, and cart_order.user is not
            session.pop('cart_id')
            return None
        elif not cart_order.user and g.user:
            # We have logged in and cart in session is not tied to this user.
            # Any old carts should be taken away - mark them as error
            Order.objects(status='cart', user=g.user).update(status='error', internal_comment='Replaced by new cart')
            # Set cart from session as new user cart
            cart_order.user = g.user
            cart_order.save()
        return cart_order
    elif g.user:
        # We have a user but no cart_id in session yet, so someone has just logged in
        cart_order = Order.objects(user=g.user, status='cart').first()
        if cart_order:
            session['cart_id'] = cart_order.id
        return cart_order
    else:
        return None


# This injects the "cart_items" into templates in shop_app
@shop_app.context_processor
def inject_cart():
    cart_order = get_cart_order()
    return dict(cart_items=cart_order.total_items if cart_order else 0)


@current_app.template_filter('currency')
def currency(value):
    return ("{:.0f}" if float(value).is_integer() else "{:.2f}").format(value)
