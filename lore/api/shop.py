"""
  controller.shop
  ~~~~~~~~~~~~~~~~

  This is the controller and Flask blueprint for a basic webshopg. It will
  setup the URL routes based on Resource and provide a checkout flow. It
  also hosts important return URLs for the payment processor.

  :copyright: (c) 2014 by Helmgast AB
"""
import logging
from datetime import datetime

import stripe
from flask import Blueprint, current_app, g, request, url_for, redirect, abort, session, flash, Markup, render_template
from flask_babel import lazy_gettext as _
from flask_classy import route
from flask_mongoengine.wtf import model_form
from mongoengine import NotUniqueError, ValidationError, Q
from wtforms.fields import FormField, FieldList, StringField
from wtforms.fields.html5 import EmailField, IntegerField
from wtforms.utils import unset_value
from wtforms.validators import InputRequired, Email, NumberRange

from lore.api.mailer import send_mail
from lore.api.resource import (ResourceAccessPolicy,
                                ImprovedModelConverter, ImprovedBaseForm, ResourceView,
                                filterable_fields_parser, prefillable_fields_parser, ListResponse, ItemResponse,
                                Authorization)
from lore.model.misc import set_lang_options, filter_is_user
from lore.model.shop import Address, Order, OrderLine, OrderStatus, Product, ProductStatus, Stock, products_owned_by_user
from lore.model.user import User
from lore.model.world import Publisher, World, filter_authorized_by_publisher

logger = current_app.logger if current_app else logging.getLogger(__name__)

shop_app = Blueprint('shop', __name__)

stripe.api_key = current_app.config['STRIPE_SECRET_KEY']


def get_or_create_stock(publisher):
    stock = Stock.objects(publisher=publisher).first()
    if not stock:
        stock = Stock(publisher=publisher)
        stock.save()
    return stock


def filter_product_published():
    return Q(status__ne=ProductStatus.hidden, created__lte=datetime.utcnow())


class ProductAccessPolicy(ResourceAccessPolicy):
    def is_editor(self, op, user, res):
        if res.publisher and user in res.publisher.editors:
            return Authorization(True, _('Allowed access to %(op)s "%(res)s" as editor', op=op, res=res),
                                 privileged=True)
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not an editor', op=op, res=res))

    def is_reader(self, op, user, res):
        if res.publisher and user in res.publisher.readers:
            return Authorization(True, _('Allowed access to %(op)s "%(res)s" as reader', op=op, res=res),
                                 privileged=True)
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not a reader', op=op, res=res))

    def is_resource_public(self, op, res):
        return Authorization(True, _("Public resource")) if res.status != 'hidden' else \
            Authorization(False, _("Not a public resource"))

    def custom_auth(self, op, user, res):
        if op == 'my_products':
            return self.is_user(op, user, res)
        else:
            return Authorization(False, _("No authorization implemented for %(op)s", op=op), error_code=403)


class ProductsView(ResourceView):
    subdomain = '<pub_host>'
    access_policy = ProductAccessPolicy()
    model = Product
    list_template = 'shop/product_list.html'
    list_arg_parser = filterable_fields_parser(['created', 'type', 'world', 'price'])
    item_template = 'shop/product_item.html'
    item_arg_parser = prefillable_fields_parser(['created', 'type', 'world', 'price'])
    form_class = model_form(Product,
                            base_class=ImprovedBaseForm,
                            exclude=['slug'],
                            converter=ImprovedModelConverter())
    # Add stock count as a faux input field of the ProductForm
    # form_class.stock_count = IntegerField(label=_("Remaining Stock"), validators=[InputRequired(), NumberRange(min=-1)])

    def index(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)
        products = Product.objects().order_by('type', '-created')
        r = ListResponse(ProductsView, [('products', products), ('publisher', publisher)])
        if not (g.user and g.user.admin):
            r.query = r.query.filter(
                filter_product_published() |
                filter_authorized_by_publisher(publisher))
        r.set_theme('publisher', publisher.theme)
        r.auth_or_abort(res=publisher)
        r.prepare_query()
        if r.args.get('fields', None) and r.args['fields'].get('world', None):
            world = World.objects(slug=r.args['fields'].get('world', "")).first()
            r.world = world

        return r

    def my_products(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)
        # products = Product.objects().order_by('type', '-created')

        products = list(products_owned_by_user(g.user))
        grouped = {}
        for p in products:
            grouped.setdefault(p.world or p.family, []).append(p)
        for group in grouped.values():
            group.sort(key=lambda p: p.publish_date or str(p.created), reverse=True)
        
        # products above is not a query, but a set generated from a for loop. This makes it impossible
        # to use paging or query args on it.

        r = ListResponse(ProductsView, [('products', []), ('publisher', publisher)])
        # if not (g.user and g.user.admin):
        #     r.query = r.query.filter(
        #         filter_product_published() |
        #         filter_authorized_by_publisher(publisher))
        r.set_theme('publisher', publisher.theme)
        r.auth_or_abort(res=publisher)
        r.template = "shop/my_products.html"
        r.my_products = grouped

        # r.prepare_query()

        return r

    def get(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        if id == 'post':
            r = ItemResponse(ProductsView, [('product', None), ('publisher', publisher)], extra_args={'intent': 'post'})
            r.set_theme('publisher', publisher.theme)
            r.auth_or_abort(res=publisher)
        else:
            product = Product.objects(slug=id).first_or_404()
            # We will load the stock count from the publisher specific Stock object
            # stock = get_or_create_stock(publisher)
            # stock_count = stock.stock_count.get(product.slug, None)
            # extra_form_args = {} if stock_count is None else {'stock_count': stock_count}
            r = ItemResponse(ProductsView, [('product', product), ('publisher', publisher)])
            # r.stock = stock
            r.set_theme('publisher', publisher.theme)
            r.auth_or_abort()

        return r

    def post(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        r = ItemResponse(ProductsView, [('product', None), ('publisher', publisher)], method='post')
        r.set_theme('publisher', publisher.theme)
        r.auth_or_abort(res=publisher)
        # r.stock = get_or_create_stock(publisher)
        product = Product()
        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(product)
        try:
            r.commit(new_instance=product)
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        # r.stock.stock_count[product.slug] = r.form.stock_count.data
        # r.stock.save()
        return redirect(r.args['next'] or url_for('shop.ProductsView:get', id=product.slug))

    def patch(self, id):

        # fa = []
        # for i in request.form.getlist('images'):
        #     fa.append(FileAsset.objects(id=i).first())
        # print fa

        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        product = Product.objects(slug=id).first_or_404()
        r = ItemResponse(ProductsView, [('product', product), ('publisher', publisher)], method='patch')
        r.set_theme('publisher', publisher.theme)
        r.auth_or_abort()
        # r.stock = get_or_create_stock(publisher)

        if not r.validate():
            return r, 400  # Respond with same page, including errors highlighted
        r.form.populate_obj(product, list(request.form.keys()))  # only populate selected keys

        try:
            r.commit()
            # r.stock.stock_count[product.slug] = r.form.stock_count.data
            # r.stock.save()
        except (NotUniqueError, ValidationError) as err:
            return r.error_response(err)
        return redirect(r.args['next'] or url_for('shop.ProductsView:get', id=product.slug))

    def delete(self, id):
        abort(503)  # Unsafe to delete products as they are referred to in orders
        # publisher = Publisher.objects(slug=publisher).first_or_404()
        # product = Product.objects(slug=id).first_or_404()
        # r = ItemResponse(ProductsView, [('product', product), ('publisher', publisher)], method='delete')
        # r.auth_or_abort()
        # r.set_theme('publisher', publisher.theme)
        # r.commit()
        # stock = Stock.objects(publisher=publisher).first()
        # if stock:
        #     del stock.stock_count[product.slug]
        #     stock.save()
        # return redirect(r.args['next'] or url_for('shop.ProductsView:index', pub_host=publisher.slug))


ProductsView.register_with_access(shop_app, 'product')


@shop_app.route('/', subdomain='<pub_host>')
def shop_home():
    if ProductsView.access_policy.authorize(op='list'):
        return redirect(url_for('shop.ProductsView:index'))
    else:
        return redirect(url_for('shop.OrdersView:my_orders'))


# shop_app.add_url_rule('/', endpoint='shop_home', subdomain='<publisher>', redirect_to='/shop/products/')

CartOrderLineForm = model_form(OrderLine, only=['quantity'], base_class=ImprovedBaseForm, converter=ImprovedModelConverter())
# Orderlines that only include comments, to allow for editing comments but not the order lines as such
LimitedOrderLineForm = model_form(OrderLine, only=['comment'], base_class=ImprovedBaseForm, converter=ImprovedModelConverter())
AddressForm = model_form(Address, base_class=ImprovedBaseForm, converter=ImprovedModelConverter())


class FixedFieldList(FieldList):
    # TODO
    # Below is a very hacky approach to handle updating the order_list. When we send in a form
    # with a deleted row, it never appears in formdata. For example, we have a order_list of 2 items,
    # when the first is deleted only the second is submitted. Below code uses the indices of the
    # field ids, e.g. order_lines-0 and order_lines-1 to identify what was removed, and then
    # process and populate the right item from the OrderList field of the model.
    # This should be fixed by wtforms!

    def process(self, formdata, data=unset_value):
        print('FieldList process formdata %s, data %s' % (formdata, data))
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
                    print("Got obj_data %s" % obj_data)
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
        for field, data in zip(self.entries, candidates):
            fake_obj = _fake()
            fake_obj.data = data
            field.populate_obj(fake_obj, 'data')
            output.append(fake_obj.data)

        setattr(obj, name, output)


class BuyForm(ImprovedBaseForm):
    product = StringField(validators=[InputRequired(_("Please enter your email address."))])


class CartForm(ImprovedBaseForm):
    order_lines = FixedFieldList(FormField(CartOrderLineForm))


class DetailsForm(ImprovedBaseForm):
    shipping_address = FormField(AddressForm)
    email = EmailField("Email", validators=[
        InputRequired(_("Please enter your email address.")),
        Email(_("Please enter your email address."))])


class PaymentForm(ImprovedBaseForm):
    order_lines = FixedFieldList(FormField(LimitedOrderLineForm))
    stripe_token = StringField(validators=[InputRequired(_("Error, missing Stripe token"))])


class PostPaymentForm(ImprovedBaseForm):
    order_lines = FixedFieldList(FormField(LimitedOrderLineForm))


class OrdersAccessPolicy(ResourceAccessPolicy):
    def is_editor(self, op, user, res):
        return Authorization(False, _("No editor access to orders"))

    def is_reader(self, op, user, res):
        if user and user == res.user:
            return Authorization(True, _('Allowed access to %(op)s "%(res)s" as owner of order', op=op, res=res),
                                 privileged=True)
        else:
            return Authorization(False, _('Not allowed access to %(op)s "%(res)s" as not owner of order', op=op, res=res))

    def authorize(self, op, user=None, res=None):
        auth = super(OrdersAccessPolicy, self).authorize(op, user, res)
        if not user:
            user = g.user
        # Need to add requirement to be user to list orders
        if op == 'list':
            return auth and self.is_user(op, user, res)
        else:
            return auth

    def custom_auth(self, op, user, res):
        if op == 'my_orders':
            return self.is_user(op, user, res)
        elif op == 'key':
            return self.is_user(op, user, res)
        else:
            return Authorization(False, _("No authorization implemented for %(op)s", op=op), error_code=403)


class OrdersView(ResourceView):
    subdomain = '<pub_host>'
    access_policy = OrdersAccessPolicy()
    model = Order
    list_template = 'shop/order_list.html'
    list_arg_parser = filterable_fields_parser(
        ['id', 'user', 'created', 'updated', 'status', 'total_price', 'total_items'])
    item_template = 'shop/order_item.html'
    item_arg_parser = prefillable_fields_parser(
        ['id', 'user', 'created', 'updated', 'status', 'total_price', 'total_items'])
    form_class = model_form(Order,
                            base_class=ImprovedBaseForm,
                            only=['order_lines', 'shipping_address', 'shipping_mobile'],
                            converter=ImprovedModelConverter())

    def index(self):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        orders = Order.objects().order_by('-updated')  # last updated will show paid highest

        r = ListResponse(OrdersView, [('orders', orders), ('publisher', publisher)])
        r.set_theme('publisher', publisher.theme if publisher else None)

        r.auth_or_abort(res=publisher)
        if not (g.user and g.user.admin):
            r.query = r.query.filter(
                filter_is_user() |
                filter_authorized_by_publisher(publisher))
        r.prepare_query()
        aggregate = list(r.orders.aggregate({'$group':
            {
                '_id': None,
                'total_value': {'$sum': '$total_price'},
                'min_created': {'$min': '$created'},
                'max_created': {'$max': '$created'}
            }
        }))
        r.aggregate = aggregate[0] if aggregate else None

        return r

    def my_orders(self):
        publisher = Publisher.objects(slug=g.pub_host).first()
        set_lang_options(publisher)

        orders = Order.objects(user=g.user).order_by('-created')  # last created shown first
        r = ListResponse(OrdersView, [('orders', orders), ('publisher', publisher)], method='my_orders', extra_args={"view": "cards"})
        r.set_theme('publisher', publisher.theme if publisher else None)
        r.auth_or_abort(res=publisher)
        if not (g.user and g.user.admin):
            r.query = r.query.filter(
                filter_is_user() |
                filter_authorized_by_publisher(publisher))
        r.prepare_query()
        r.template = "shop/my_orders.html"
        return r

    def get(self, id):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        # TODO we dont support new order creation outside of cart yet
        # if id == 'post':
        #     r = ItemResponse(OrdersView, [('order', None), ('publisher', publisher)], extra_args={'intent': 'post'})
        order = Order.objects(id=id).get_or_404()  # get_or_404 handles exception if not a valid object ID
        r = ItemResponse(OrdersView, [('order', order), ('publisher', publisher)], form_class=PostPaymentForm)
        r.set_theme('publisher', publisher.theme)
        r.auth_or_abort()
        return r

    @route('/key/<code>', methods=['GET', 'PATCH'])
    def key(self, code):
        # Custom authentication
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        order = Order.objects(external_key=code).get_or_404()  # get_or_404 handles exception if not a valid object ID

        r = ItemResponse(OrdersView, [('order', order), ('publisher', publisher)], method='key', extra_args={'intent': 'patch'})
        r.set_theme('publisher', publisher.theme)
        if not g.user:
            return render_template("error/401.html", root_template='_root.html', publisher_theme=r.publisher_theme)
        r.auth_or_abort()
        r.template = "shop/order_peek.html"
        r.code = code
        if request.method in ['PATCH'] and not (order.user or order.email):  # Key hasn't already been activated for this order
            r.method = "patch"
            order.user = g.user
            order.status = OrderStatus.paid
            try:
                r.commit()
            except (NotUniqueError, ValidationError) as err:
                return r.error_response(err)
            return redirect(r.args['next'] or url_for('shop.OrdersView:get', id=order.id))
        return r

    def patch(self, id, publisher):
        abort(501)  # Not implemented

    @route('/buy', methods=['PATCH'])
    def buy(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        cart_order = get_cart_order()
        r = ItemResponse(OrdersView, [('order', cart_order), ('publisher', publisher)], form_class=BuyForm,
                         method='patch')
        r.auth = Authorization(True, _('Always allowed'))
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
                session['cart_id'] = str(cart_order.id)
                r.instance = cart_order  # set it in the response as well
            found = False
            for ol in cart_order.order_lines:
                if ol.product == p:
                    ol.quantity += 1
                    found = True
            if not found:  # create new orderline with this product
                new_ol = OrderLine(product=p, price=p.price)
                cart_order.order_lines.append(new_ol)
            try:
                cart_order.save()
            except (NotUniqueError, ValidationError) as err:
                return r.error_response(err)
            return r
        abort(400, 'Badly formed cart patch request')

    # Post means go to next step, patch means to stay
    @route('/cart', methods=['GET', 'PATCH', 'POST'])
    def cart(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        cart_order = get_cart_order()
        r = ItemResponse(OrdersView, [('order', cart_order), ('publisher', publisher)], form_class=CartForm,
                         extra_args={'view': 'cart', 'intent': 'post'})
        r.auth = Authorization(True, _('Always allowed'))

        r.set_theme('publisher', publisher.theme)
        if request.method in ['PATCH', 'POST']:
            r.method = request.method.lower()
            if not r.validate():
                return r, 400  # Respond with same page, including errors highlighted
            r.form.populate_obj(cart_order)  # populate all of the object
            try:
                r.commit(flash=False)
            except (NotUniqueError, ValidationError) as err:
                return r.error_response(err)
            if request.method == 'PATCH':
                return redirect(r.args['next'] or url_for('shop.OrdersView:cart', **request.view_args))
            elif request.method == 'POST':
                return redirect(r.args['next'] or url_for('shop.OrdersView:details', **request.view_args))
        return r  # we got here if it's a get

    @route('/details', methods=['GET', 'POST'])
    def details(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        cart_order = get_cart_order()
        if not cart_order or cart_order.total_items < 1:
            return redirect(url_for('shop.OrdersView:cart'))

        r = ItemResponse(OrdersView, [('order', cart_order), ('publisher', publisher)], form_class=DetailsForm,
                         extra_args={'view': 'details', 'intent': 'post'})
        r.auth = Authorization(True, _('Always allowed'))

        r.set_theme('publisher', publisher.theme)
        if request.method == 'POST':
            r.method = 'post'
            if not r.validate():
                return r, 400  # Respond with same page, including errors highlighted
            r.form.populate_obj(cart_order)  # populate all of the object
            if not g.user and User.query_user_by_email(email=cart_order.email)[:1]:
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
            except (NotUniqueError, ValidationError) as err:
                return r.error_response(err)
            return redirect(r.args['next'] or url_for('shop.OrdersView:pay', **request.view_args))
        return r  # we got here if it's a get

    @route('/pay', methods=['GET', 'POST'])
    def pay(self):
        publisher = Publisher.objects(slug=g.pub_host).first_or_404()
        set_lang_options(publisher)

        cart_order = get_cart_order()
        if not cart_order or not cart_order.shipping_address or not cart_order.user:
            return redirect(url_for('shop.OrdersView:cart'))
        r = ItemResponse(OrdersView, [('order', cart_order), ('publisher', publisher)], form_class=PaymentForm,
                         extra_args={'view': 'pay', 'intent': 'post'})
        r.auth = Authorization(True, _('Always allowed'))

        r.set_theme('publisher', publisher.theme)
        r.stripe_key = current_app.config['STRIPE_PUBLIC_KEY']
        if request.method == 'POST':
            r.method = 'post'
            if not r.validate():
                return r, 400  # Respond with same page, including errors highlighted
            r.form.populate_obj(cart_order)  # populate all of the object
            # Remove the purchased quantities from the products, ensuring we don't go below zero
            # If failed, the product has no more stock, we have to abort purchase
            stock_available = cart_order.deduct_stock(publisher)
            if not stock_available:
                r.errors = [('danger', 'A product in this order is out of stock, purchase cancelled')]
                return r, 400
            try:
                # Will raise CardError if not succeeded
                charge = stripe.Charge.create(
                    source=r.form.stripe_token.data,
                    amount=cart_order.total_price_int(),  # Stripe takes input in "cents" or similar
                    currency=cart_order.currency,
                    description=str(cart_order),
                    metadata={'order_id': cart_order.id}
                )
                cart_order.status = OrderStatus.paid
                cart_order.charge_id = charge['id']

                r.commit()
                g.user.log(action='purchase', resource=cart_order, metric=cart_order.total_price_sek())
                send_mail(recipients=[g.user.email], message_subject=_('Thank you for your order!'), mail_type='order',
                          cc=[current_app.config['MAIL_DEFAULT_SENDER']], user=g.user, order=cart_order,
                          publisher=publisher)
            except stripe.error.CardError as ce:
                r.errors = [('danger', ce.json_body['error']['message'])]
                return r, 400
            except ValidationError as ve:
                r.errors = [('danger', ve._format_errors())]
                return r, 400  # Respond with same page, including errors highlighted
            finally:
                # Executes at any exception from above try clause, before returning / raising
                # Return purchased quantities to the products
                cart_order.return_stock(publisher)
            return redirect(r.args['next'] or url_for('shop.OrdersView:get', id=cart_order.id, **request.view_args))
        return r  # we got here if it's a get


OrdersView.register_with_access(shop_app, 'order')


def get_cart_order():
    if session.get('cart_id', None):
        # We have a cart in the session
        cart_order = Order.objects(id=session['cart_id']).first()
        if not cart_order or cart_order.status != 'cart' or (cart_order.user and cart_order.user != g.user):
            # Error, maybe someone is manipulating input, or we logged out and should clear the
            # association with that cart for safety
            # True if current user is different, or if current user is none, and cart_order.user is not
            session.pop('cart_id')
            return None
        elif not cart_order.user and g.user:
            # We have logged in and cart in session lacks a user, means the cart came from before login
            # There may be old carts registered to this user, let's delete them, e.g. overwrite with new cart
            Order.objects(status='cart', user=g.user).delete()
            # Attach cart from session to the newly logged in user
            cart_order.user = g.user
            cart_order.save()  # Save the new cart
        return cart_order
    elif g.user:
        # We have no cart_id in session yet, but we have a user, so someone has just logged in
        # Let's find any old carts belonging to this user
        cart_order = Order.objects(user=g.user, status='cart').first()
        if cart_order:
            session['cart_id'] = cart_order.id
        return cart_order
    else:
        return None


# The main entry point for keys at lore.pub, before routing to publisher
@current_app.route('/key/<code>', subdomain=current_app.default_host)
def key(code):
    order = Order.objects(external_key=code).first()
    if order and order.publisher:
        return redirect(url_for('shop.OrdersView:key', code=code, pub_host=order.publisher.slug))
    else:
        abort(404, description=_("This code doesn't exist or haven't been added yet. Double check that you typed it correctly, otherwise contact your publisher for more information."))

# This injects the "cart_items" into templates in shop_app
@shop_app.context_processor
def inject_cart():
    cart_order = get_cart_order()
    return dict(cart_items=cart_order.total_items if cart_order else 0)
