import re
from datetime import date, datetime, timedelta
from typing import Sequence

from flask import g, request
from flask_babel import get_locale, gettext
from flask_babel import lazy_gettext as _
from html2text import html2text
from mongoengine import (
    CASCADE,
    DENY,
    NULLIFY,
    BooleanField,
    DateTimeField,
    EmailField,
    EmbeddedDocument,
    EmbeddedDocumentField,
    FloatField,
    IntField,
    ListField,
    MapField,
    ReferenceField,
    StringField,
    URLField,
)
from mongoengine.errors import DoesNotExist, ValidationError
from mongoengine.fields import DictField

from lore.model.asset import get_google_urls, guess_content_type
from lore.model.misc import default_translated_nones, default_translated_strings
from lore.model.user import Event
from tools.batch import JobSuccess

from .asset import FileAccessType, FileAsset
from .misc import Document  # Enhanced document
from .misc import (
    Address,
    Choices,
    choice_options,
    datetime_delta_options,
    datetime_month_options,
    extract,
    from7to365,
    get,
    numerical_options,
    parse_datetime,
    pick_i18n,
    reference_options,
    set_if,
    slugify,
)
from .user import User, user_from_email
from .world import Publisher, World

ProductTypes = Choices(book=_("Book"), item=_("Item"), digital=_("Digital"), shipping=_("Shipping fee"))

ProductStatus = Choices(
    pre_order=_("Pre-order"),
    available=_("Available"),
    ready_for_download=_("Ready for download"),
    out_of_stock=_("Out of stock"),
    hidden=_("Hidden"),
)

# TODO replace small letters for currency keys to large, to match babel and common use
Currencies = Choices(eur="EUR", sek="SEK", usd="USD")

FX_FORMAT = {"eur": "€ %s", "sek": "%s :-", "usd": "$ %s"}

FX_IN_SEK = {"eur": 11.0, "sek": 1.0, "usd": 10.0}

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


class Price(EmbeddedDocument):
    price = FloatField(min_value=0, default=0, required=True, verbose_name=_("Price"))
    currency = StringField(
        required=True, choices=Currencies.to_tuples(), default=Currencies.sek, verbose_name=_("Currency")
    )


class Product(Document):
    # Allows us to have a deprecated title field in DB that is not reflected here without errors
    meta = {"strict": False, "indexes": ["product_number"]}

    slug = StringField(unique=True, max_length=62)  # URL-friendly name  # needs i18n
    product_number = StringField(max_length=10, sparse=True, unique=True, verbose_name=_("Product Number"))
    project_code = StringField(max_length=10, sparse=True, verbose_name=_("Project Code"))
    title_i18n = MapField(field=StringField(max_length=99), verbose_name=_("Title"))
    description_i18n = MapField(field=StringField(), verbose_name=_("Description"))
    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, required=True, verbose_name=_("Publisher"))
    publish_date = StringField(max_length=20, verbose_name=_("Publishing Date"))
    world = ReferenceField(World, reverse_delete_rule=DENY, verbose_name=_("World"))
    family = StringField(max_length=60, verbose_name=_("Product Family"))
    created = DateTimeField(default=datetime.utcnow, verbose_name=_("Created"))
    updated = DateTimeField(default=datetime.utcnow, verbose_name=_("Updated"))
    type = StringField(choices=ProductTypes.to_tuples(), required=True, verbose_name=_("Type"))
    # TODO should be required=True, but that currently maps to Required, not InputRequired validator
    # Required will check the value and 0 is determined as false, which blocks prices for 0
    # TODO price as a MapField, similar to i18n
    price = FloatField(min_value=0, default=0, verbose_name=_("Price"))
    prices = ListField(EmbeddedDocumentField(Price))
    tax = FloatField(
        min_value=0, default=0.25, choices=[(0.25, "25%"), (0.06, "6%"), (0, "0% (Auto)")], verbose_name=_("Tax")
    )
    currency = StringField(
        required=True, choices=Currencies.to_tuples(), default=Currencies.sek, verbose_name=_("Currency")
    )
    # Not a URLField because it wouldn't accept empty strings
    shop_url_i18n = MapField(
        field=StringField(), verbose_name=_("Product webshop URL"), default=default_translated_strings
    )
    downloads = ListField(ReferenceField(FileAsset, reverse_delete_rule=DENY), verbose_name=_("Downloads"))
    status = StringField(choices=ProductStatus.to_tuples(), default=ProductStatus.available, verbose_name=_("Status"))
    images = ListField(ReferenceField(FileAsset, reverse_delete_rule=NULLIFY), verbose_name=_("Product Images"))

    # TODO DEPRECATE in DB version 3
    feature_image = ReferenceField(FileAsset, reverse_delete_rule=NULLIFY, verbose_name=_("Feature Image"))
    acknowledgement = BooleanField(default=False, verbose_name=_("Name in book"))
    comment_instruction = StringField(
        max_length=20, verbose_name=_("Instructions for comments in order")
    )  # needs i18n
    # Deny removal of downloadable files as people will lose access

    # Executes before saving
    def clean(self):
        self.updated = datetime.utcnow()
        self.slug = slugify(self.product_number)

    def slug_path(self):
        return f"{self.world.slug if self.world else 'meta'}/{self.slug or slugify(self.product_number)}/"

    def get_price(self, currency=None):
        """Returns price per currency, in a backwards compatible manner as price format has changed"""
        if self.price is not None:  # We are using old, single-currency price
            if (currency is None) or (currency and currency == self.currency):
                return self.price
            else:
                raise ValueError(f"No price defined for {currency}")
        else:
            currency = currency or self.currency or Currencies.sek
            priceline = next(x for x in self.prices if x.currency == currency)
            return priceline.price

    @property  # For convenience
    def title(self):
        return pick_i18n(self.title_i18n)

    @title.setter
    def set_title(self):
        raise NotImplementedError()

    @property  # For convenience
    def description(self):
        return pick_i18n(self.description_i18n)

    @description.setter
    def set_description(self):
        raise NotImplementedError()

    @property  # For convenience
    def shop_url(self):
        return pick_i18n(self.shop_url_i18n)

    @shop_url.setter
    def set_shop_url(self):
        raise NotImplementedError()

    @property  # For convenience
    def get_feature_image(self):
        return self.images[0] if self.images else None

    def in_orders(self):
        # This raw query finds orders where at least on order_line includes this product
        q = Order.objects(__raw__={"order_lines": {"$elemMatch": {"product": self.id}}})
        return q

    def delete(self):
        if self.in_orders().count() > 0:
            raise ValidationError("Cannot delete product %r as it's referenced by Orders" % self)
        super(Product, self).delete()

    def is_owned_by_current_user(self):
        return g.user and self in products_owned_by_user(g.user)

    def __str__(self):
        """A string representation suitable for display to end users. Call with !s after variable in f-strings."""
        return f"{self.title} [{self.product_number}] ({self.world or self.family})"

    def __repr__(self):
        """A string representation suitable for logging and debugging. Call with !r after variable in f-strings."""
        return f"{self.__class__}('{self.pk!r}', '{self.title}', '{self.product_number}', '{self.world!r}', '{self.publisher!r}')"


Product.world.filter_options = reference_options("world", Product, id_attr="pk")
Product.type.filter_options = choice_options("type", Product.type.choices)
Product.price.filter_options = numerical_options("price", [0, 50, 100, 200])
Product.created.filter_options = datetime_delta_options("created", from7to365)


class OrderLine(EmbeddedDocument):
    quantity = IntField(min_value=1, default=1, verbose_name=_("Comment"))
    product = ReferenceField(Product, verbose_name=_("Product"))
    title = StringField(max_length=99, verbose_name=_("Item"))
    price = FloatField(min_value=0, verbose_name=_("Price"))
    # VAT is the part of price that is VAT. So ex-VAT = price - vat.
    vat = FloatField(min_value=0, verbose_name=_("VAT"))
    comment = StringField(max_length=99, verbose_name=_("Comment"))

    @property
    def get_title(self):
        if self.title:
            return self.title
        else:
            return self.product.title if self.product else _("Unknown")

    @property
    def has_price(self):
        return isinstance(self.price, float)

    def __str__(self):
        return f"{self.quantity}x{self.get_title}@{self.price}"


OrderStatus = Choices(
    cart=_("Cart"),
    checkout=_("Checkout"),
    ordered=_("Ordered"),
    paid=_("Paid"),
    shipped=_("Shipped"),
    error=_("Error"),
    discarded=_("Discarded"),
)


class Stock(Document):
    """This is a special document which holds all stock status for a publisher's products.
    It is kept as a single document, to ensure that we can do single document atomic updates
    using mongodb, without too much trouble. E.g. we can update the stock status of a full OrderLine
    with one command and one lock.
    """

    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, unique=True, verbose_name=_("Publisher"))
    updated = DateTimeField(default=datetime.utcnow, verbose_name=_("Updated"))
    stock_count = MapField(field=IntField(min_value=-1, default=0))

    def clean(self):
        self.updated = datetime.utcnow()

    def display_stock(self, product):
        if product in self.stock_count:
            if self.stock_count[product] < 0:
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
    meta = {
        # "strict": False,
        "indexes": [
            {
                "fields": ["external_key"],  # Does unique but not for null fields
                "unique": True,
                "partialFilterExpression": {"external_key": {"$type": "string"}},
            },
        ],
    }

    title = StringField(max_length=60, verbose_name=_("Title"))  # needs i18n
    external_key = StringField(null=True, verbose_name=_("External Key"))
    user = ReferenceField(User, reverse_delete_rule=DENY, verbose_name=_("User"))
    publisher = ReferenceField(Publisher, reverse_delete_rule=DENY, verbose_name=_("Publisher"))
    session = StringField(verbose_name=_("Session ID"))
    email = EmailField(max_length=60, verbose_name=_("Email"))
    order_lines = ListField(EmbeddedDocumentField(OrderLine))
    total_items = IntField(min_value=0, default=0, verbose_name=_("# items"))
    total_price = FloatField(min_value=0, default=0.0, verbose_name=_("Total price"))  # Incl shipping
    total_tax = FloatField(min_value=0, default=0.0, verbose_name=_("Total tax"))
    currency = StringField(choices=Currencies.to_tuples(), verbose_name=_("Currency"))
    created = DateTimeField(default=datetime.utcnow, verbose_name=_("Created"))
    updated = DateTimeField(default=datetime.utcnow, verbose_name=_("Updated"))
    status = StringField(choices=OrderStatus.to_tuples(), default=OrderStatus.cart, verbose_name=_("Status"))
    shipping_line = EmbeddedDocumentField(OrderLine)
    source_url = URLField(verbose_name=_("Source URL"))
    message = StringField(verbose_name=_("Customer message"))
    charge_id = StringField()  # Stores the Stripe charge id
    internal_comment = StringField(verbose_name=_("Internal Comment"))
    shipping_address = EmbeddedDocumentField(Address)

    def __str__(self):
        """A string representation suitable for display to end users. Call with !s after variable in f-strings."""
        if self.title:
            return self.title
        max_line, max_price = None, -1
        for ol in self.order_lines:
            if ol.price is not None and ol.price > max_price:
                max_line, max_price = str(ol.title or ol.product), ol.price
        if max_line:
            more = self.total_items - 1
            suffix = _(" and %(more)s more", more=more) if more else ""
            s = f"{max_line}{suffix}"
        else:
            s = f"{_('Empty order')}"
        return s

    def __repr__(self):
        """A string representation suitable for logging and debugging. Call with !r after variable in f-strings."""
        return f"{self.__class__}('{self.pk!r}', '{self.title}', '{self.external_key}', '{self.user!r}', '{self.status!r}')"

    @staticmethod
    def calc_vat(price, rate):
        return price - price / (1 + rate)

    def calc_shipping_vat_rate(self):
        acc = 0.0
        tot_price = 0.0
        for ol in self.order_lines:
            if ol.price and ol.vat is not None:
                acc += ol.price * ol.vat / (ol.price - ol.vat)
                tot_price += ol.price
        return acc / tot_price if tot_price > 0.0 else 0.0

    def is_paid_or_shipped(self):
        return self.status in [OrderStatus.paid, OrderStatus.shipped]

    def is_digital(self):
        """True if this order only contains products of type Digital"""
        for ol in self.order_lines:
            if ol.product.type != ProductTypes.digital:
                return False
        # True if there was lines in order, false if not
        return len(self.order_lines) > 0

    def has_downloads(self):
        """True if this order contains some products with downloadable files"""
        for ol in self.order_lines:
            if ol.product and len(ol.product.downloads) > 0:
                return True
        # True if there was lines in order, false if not
        return False

    def total_price_int(self):
        """Returns total price as an int, suitable for Stripe"""
        return int(self.total_price * 100)

    def total_price_sek(self):
        """Returns total price as an int in SEK equivalent based on pre-defined FX rate"""
        return int(self.total_price * FX_IN_SEK[self.currency])

    def total_price_display(self):
        price_format = ("{:.0f}" if float(self.total_price).is_integer() else "{:.2f}").format(self.total_price)
        fx_format = FX_FORMAT.get(self.currency, "%s")
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
            select_args, update_args = {}, {}
            for prod, quantity in order_dict.items():
                if select_op:  # We only need to do this check when reducing quantity
                    select_args["stock_count__%s__%s" % (prod, select_op)] = quantity
                update_args["%s__stock_count__%s" % (update_op, prod)] = quantity
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
        return self.update_stock(publisher, "dec", "gte")

    def return_stock(self, publisher):
        return self.update_stock(publisher, "inc")

    # Executes before saving
    def clean(self):
        self.updated = datetime.utcnow()
        num, tot_price, tot_vat = 0, 0.0, 0.0
        for ol in self.order_lines:
            num += ol.quantity
            if ol.price:
                tot_price += ol.price
                tot_vat += ol.vat if type(ol.vat) == int or type(ol.vat) == float else 0
        if self.shipping_line:
            tot_price += self.shipping_line.price
            tot_vat += self.shipping_line.vat if type(self.shipping_line.vat) == float else 0
        self.total_items = num  # Excludes shipping
        self.total_price = tot_price
        self.total_tax = tot_vat
        if self.user and not self.email:
            self.email = self.user.email


Order.total_items.filter_options = numerical_options("total_items", [0, 1, 3, 5])
Order.total_price.filter_options = numerical_options("total_price", [0, 50, 100, 200])
Order.status.filter_options = choice_options("status", Order.status.choices)
Order.created.filter_options = datetime_month_options("created")
Order.updated.filter_options = datetime_delta_options(
    "updated", [timedelta(days=1), timedelta(days=7), timedelta(days=30), timedelta(days=90), timedelta(days=365)]
)


def products_owned_by_user(user):
    products = set()
    if user:
        orders = Order.objects(user=user, status__in=[OrderStatus.paid, OrderStatus.shipped]).only("order_lines")
        for order in orders:
            for order_line in order.order_lines:
                if order_line.product:
                    products.add(order_line.product)
    return products


def user_has_asset(user, asset):
    products = products_owned_by_user(user)
    for p in products:
        if p.downloads and asset in p.downloads:
            return True
    return False


def parse_price(p_string):
    rv = {}
    if p_string:
        try:
            for el in p_string.split("|"):
                el = el.strip()
                if not el:
                    continue
                cur, price = el.split(" ", 1)
                cur = cur.lower()
                if not cur or cur not in Currencies:
                    continue
                rv[cur] = float("0" + price.replace(",", ""))  # The "0"+ is a trick to coerce empty string to float
        except Exception as e:
            raise ValueError(f"Couldn't parse price string '{p_string}'") from e
    return rv


def parse_url_assets(urls, document, commit=False, slug_prefix="", locked_to_product=False):
    if isinstance(urls, str):
        urls = [u.strip() for u in urls.split("|") if len(u.strip()) > 0]
    fa_list = []
    for url in urls:
        out = {"source_file_url": url}  # Assume first its a plain str url
        if isinstance(url, str) and " http" in url:
            # We can receive a title before the link, like 'title.pdf http://mylink'
            url = url.split(" http")
            url[1] = "http" + url[1]
        if (isinstance(url, tuple) or isinstance(url, list)) and len(url) > 1:
            out["title"] = url[0]
            out["source_file_url"] = url[1]
        google_urls = get_google_urls(out["source_file_url"])
        if google_urls:
            out["source_file_url"] = google_urls["direct"]
        fa = FileAsset.objects(source_file_url=out["source_file_url"]).first()
        # TODO may break if URL is different but slug ends up the same
        if not fa:
            fa = FileAsset(publisher=document.publisher, **out)
            if fa.title:
                # A hack, if we trust the name and source, this means we will skip the URL sniffing
                fa.source_filename = fa.title
                ctype = guess_content_type(fa.title)
                if ctype:
                    fa.content_type = ctype
            if locked_to_product:
                fa.access_type = FileAccessType.product
            if commit:
                fa.clean()
                fa.slug = slug_prefix + fa.slug
                fa.save(clean=False)

        fa_list.append(fa)
    return fa_list


# https://regex101.com/r/4HgdwB/1/. match string like 100xNNN-123@12*0.25 where
# 100 is qty, NNN-123 is product, 12 is price and 0.25 is vatRate. Missing price is
# interpeted as no price (not zero price).
ol_pattern = re.compile(r"^(?:(\d+)x)?([^@#]+)(?:#([^@]+))?(?:@([\d.,]+)\*([\d.,]+))?$")


def parse_orderlines(order_lines, lookup_product_with_currency=None, job=None):
    """Parses a string into a list of OrderLines. Accepts strings like:
    2xNNN-123#comment@12*0.25|NNN-123|Some product title row@100*0.25. Format is:
    {quantity}x{product}#{comment}@{price}*{vatRate}. Quantity, comment and price with vatRate are optional.
    Will attempt to get price and VAT from the product in database, unless defaults have been provided.

    Arguments:
        order_lines {str or list} -- a string to split by '|' or a list

    Keyword Arguments:
        lookup_product_with_currency {str} -- currency to use to look up products, if not set no product lookups will be made (default: {None})

    Raises:
        ValueError: [description]

    Returns:
        list -- of OrderLines
    """

    if isinstance(order_lines, str):
        order_lines = [ol.strip() for ol in re.split(r"[|\n]", order_lines)]
    if not isinstance(order_lines, list):
        raise ValueError(f"Incorrect string or list of orderlines: {order_lines}")

    ols = []
    for ol in order_lines:
        matches = extract(ol, ol_pattern, default=None, groups=5)
        ol = OrderLine()
        if not matches[1]:
            continue
        product = Product.objects(product_number=matches[1]).first()
        if product:
            ol.product = product
        else:
            if job:
                job.warn(f"Couldn't find product {matches[1]}, using as line title instead")
            ol.title = matches[1]

        ol.quantity = 1 if matches[0] is None else int(matches[0])

        # OrderLine price and vat is total for the line, so multiply prices by quantity
        if matches[2] is not None:
            ol.comment = matches[2]

        if matches[3] is not None:
            ol.price = ol.quantity * float(matches[3])
            ol.vat = Order.calc_vat(ol.price, float(matches[4]))
        elif product and lookup_product_with_currency:
            ol.price = ol.quantity * product.get_price(lookup_product_with_currency)
            ol.vat = Order.calc_vat(ol.price, product.tax)
        else:
            pass  # Means we set no price and vat, because no currency was given. This can be intentional.

        ols.append(ol)
    return ols


def parse_i18n_field(data, field):
    out = {}
    keys = [key for key in data.keys() if re.search(field + ":\\w\\w$", key, re.IGNORECASE)]
    for key in keys:
        val = get(data, key, None)
        if val is not None:
            field, lang = key.split(":", 1)
            out[lang.lower()] = val
    return out


def job_import_order(job, data, **kwargs):
    if "publisher" not in data and "publisher" in job.context:
        data["publisher"] = job.context["publisher"]

    if "vatRate" not in data and "vatrate" in job.context:
        # Note small r, it's because keys are normalized from command line
        data["vatRate"] = job.context["vatrate"]

    if "sourceUrl" not in data and "sourceurl" in job.context:
        # Note small r, it's because keys are normalized from command line
        data["sourceUrl"] = job.context["sourceurl"]

    if "title" not in data and "title" in job.context:
        data["title"] = job.context["title"]

    return import_order(data, job=job, commit=not job.is_dry_run, **kwargs)


def import_order(data, job=None, commit=False, create=True, if_newer=True):
    """Authoritative function for importing external data to an Order object.
    Assumes a row argument as a dict, that is either flat (representing e.g. a row in a sheet)
    or nested (representing a typical JSON structure). The function will only pick out
    properties it recognizes and will ignore rest of data.

    At minimum, input needs the following fields:
    * external_key
    * order_lines (list or comma-separated string of product numbers)
    * publisher
    If we get an email/user_id, the order will be created as "paid" to that user. Otherwise,
    we will treat is an an unclaimed order (stats "ordered", currently)
    Users or products that cannot be found in database

    Currently handled formats:

    Abicart/Textalk Order: https://api.textalk.se/webshop/api-classes/Order/, sample
    in tests/textalk_order.json


    Kickstarter Backer Report exported table row as dict
    {
        "Backer Number": "1",
        "Backer UID": "1647400540",
        "Backer Name": "Kalle Henricson",
        "Email": "kalle.henricson@gmail.com",
        "Shipping Country": "SE",
        "Shipping Amount": "SEK 100.00",
        "Reward Title": "Basare",
        "Reward Minimum": "SEK 650.00",
        "Reward ID": "6526680",
        "Pledge Amount": "SEK 750.00",
        "Pledged At": "2018/03/28, 10:27",
        "Rewards Sent?": "",
        "Pledged Status": "collected",
        "Notes": "",
        "Billing State/Province": "",
        "Billing Country": "SE",
        "Survey Response": "2018/05/26, 14:05",
        "Shipping Name": "Kalle Henricson",
        "Shipping Address 1": "Granängsringen 15 Lgh 1302",
        "Shipping Address 2": "",
        "Shipping City": "Tyresö",
        "Shipping State": "Stockholms Län",
        "Shipping Postal Code": "135 44",
        "Shipping Country Name": "Sweden",
        "Shipping Country Code": "SE",
        "Shipping Phone Number": "",
        "Shipping Delivery Notes: "",

        "Order Lines": "NEO-100D,NEO-101D,NEO-102D",   # Order Lines is not provided by Kickstarter, need to be added by us
        "Publisher": "helmgast.se",  # Publisher need to be added by us at import
        "Title": "Neotech Edge Kickstarter",  # Title need to be added by us at import
        # external_key should be set from Backer UID and Reward ID to be unique.
    }

    Manual, minimal import (e.g. for voucher)
    {
        'Key': 'UNIQUE CODE',  # Need to always provide a unique code, to avoid double importing at later stage.
        'Email': 'slaizt@gmail.com',
        'Level': 'Basare',
        'Publisher': 'helmgast.se',
        'Order Lines': 'NEO-100D,NEO-101D,NEO-102D',
        'Title': 'Neotech Edge Kickstarter Bas-cert'
    }

    Examples of different key case variations:
    Order Lines - Sheet or CSV header
    orderLines - camelCase

    """
    # If a field exist in data, we should overwrite what's in the order. It includes the ability to set values to empty values (except setting to None)

    # TODO handle missing variant/choice products
    # TODO warn if KS is missing title, vat, publisher

    # An order requires that we have an external key, publisher and order lines
    key = get(data, "key", None) or get(data, "uid", None)
    if not key:
        if job:
            job.warn("A key/external_key/orderid is required when importing. Make sure it's unique.")
        return None
    key = str(key).split("/")[-1]  # Split in case it starts with a URL

    order = Order.objects(external_key=key).first()

    if order:
        is_updating = True  # We are patching an existing object
        # There is an existing order
        if if_newer:
            # Only update if newer
            changed = (
                parse_datetime(get(data, "changed", None))
                or parse_datetime(get(data, "updated", None))
                or parse_datetime(get(data, "imported", None))
            )
            # Commented out as this means we can't update without setting imported to a future date.
            # Downside is that because we don't write import timestamps by default back to sheets, this makes it easier
            # to accidentally re-import and overwrite
            # if not changed:
            #     if job:
            #         job.warn("Couldn't get valid changed/updated time from input data to decide to update the data")
            #     return None

            # We expect both datetimes to be in UTC. But Python might still have created them as timezone naive dt-objects.
            if changed and changed.replace(tzinfo=None) <= order.updated:
                if job:
                    job.info("Skipped import as order not newer than what's already in database")
                    job.success = JobSuccess.SKIP
                return None  # Skip if we have already
    else:
        is_updating = False  # We are creating a new object from scratch
        order = Order(external_key=key)

    discarded = get(data, "discarded", None)
    if discarded is not None and discarded:
        if not is_updating:
            if job:
                job.warn(f"Order {data} is marked as discarded")
            return None
        else:
            order.status = OrderStatus.discarded

    publisher = get(data, "publisher", "")
    if publisher:  # Only accept non-empty publisher data
        order.publisher = Publisher.objects(slug=publisher).first()
    if not order.publisher and not is_updating:  # Early validation to stop if no publisher
        raise ValueError("A publisher slug/domain is required when importing.")

    lang = get(data, "language", "en")
    currency = get(data, "currency", None)
    if currency is not None:
        if currency.lower() in Currencies:
            order.currency = currency.lower()
        elif currency == "":  # An empty currency means we want to set currency blank
            order.currency = None
        else:
            raise ValueError(f"Currency {currency} not supported")
    cur = order.currency  # Shorthand

    title = get(data, "title", "")  # Don't allow setting empty titles
    rewardTitle = get(data, "rewardTitle", "")
    if title:
        order.title = f"{title}{': ' if rewardTitle else ''}{rewardTitle}"

    order_lines = get(data, "orderLines", [])
    items = get(data, "items", [])
    if order_lines and not items:
        # We have a Kickstarter or manual order that needs to be built up
        if cur and not rewardTitle:
            # Not a kickstarter Order and we have a currency. We will get prices from the listed product price.
            order_lines = parse_orderlines(order_lines, lookup_product_with_currency=cur, job=job)
        else:
            # A kickstarter order, parse without looking up any price, either not set price or use what's given in the parsed string
            order_lines = parse_orderlines(order_lines, job=job)

        deliveryMethod = get(data, "deliveryMethod", None)
        totPrice = parse_price(get(data, "pledgeAmount", None))
        rewardPrice = parse_price(get(data, "rewardMinimum", None) or get(data, "backingMinimum", None))
        shipping_price = parse_price(get(data, "shippingAmount", None))
        if not cur and (totPrice or rewardPrice or shipping_price):
            # As we have a price, we haft to have a currency for the order, and will try to gues it
            if totPrice.keys():
                order.currency = list(totPrice.keys())[0].lower()
            elif rewardPrice.keys():
                order.currency = list(rewardPrice.keys())[0].lower()
            elif shipping_price.keys():
                order.currency = list(shipping_price.keys())[0].lower()
            else:
                raise ValueError("Can't guess currency for order as no prices given with currency")
            cur = order.currency

        vatRate = get(data, "vatRate", 0)
        if isinstance(vatRate, str):
            vatRate = float("0" + vatRate)  # Small trick that makes even a blank string into a float

        if rewardTitle:
            # It's kickstarter
            if rewardPrice is None:
                rewardPrice = totPrice
            if shipping_price is None:
                shipping_price = {k: 0.0 for k in totPrice.keys()}
            subtotal = sum([ol.price for ol in order_lines if ol.price])  # Sum of all orderlines parsed
            extra_pledge = totPrice.get(cur, 0) - shipping_price.get(cur, 0) - rewardPrice.get(cur, 0) - subtotal
            order_lines.insert(
                0,
                OrderLine(
                    title=rewardTitle,
                    price=rewardPrice.get(cur, 0),
                    vat=Order.calc_vat(rewardPrice.get(cur, 0), vatRate),
                ),
            )
            if extra_pledge > 0:
                # Extra pledge is considered tax free
                order_lines.append(
                    OrderLine(title="Extra pledge", price=extra_pledge, vat=Order.calc_vat(extra_pledge, 0.0))
                )
        order.order_lines = order_lines  # Need to happen before calculating shipping
        if shipping_price and cur in shipping_price:
            order.shipping_line = OrderLine(
                title=deliveryMethod,
                price=shipping_price.get(cur, 0),
                # Automatically calculate average vat based on what's in orderlines
                vat=Order.calc_vat(shipping_price.get(cur, 0), order.calc_shipping_vat_rate()),
            )
    elif items and not order_lines:
        # We have a Textalk order with items
        for item in items:
            ol = OrderLine()
            pnum = get(item, "articleNumber")
            try:
                ol.product = Product.objects(product_number=pnum).scalar("id").as_pymongo().get()["_id"]
            except DoesNotExist as dne:
                raise ValueError(f"Product number '{pnum}' ({get(item, 'articleName', '')}) doesn't exist") from dne
            ol.quantity = get(item, "choices.quantity", 1)
            ol.price = get(item, "costs.total.incVat", 0.0)
            ol.vat = get(item, "costs.total.vat", 0.0)
            if "discountInfo" in item:
                ol.price -= get(item, "discountInfo.incVat", 0.0)
                ol.vat -= get(item, "discountInfo.vat", 0.0)
            ol.comment = get(item, "choices.choiceString", "")
            order_lines.append(ol)
        if not order_lines:
            raise ValueError(f"Items {items} did not result in any valid orderlines")
        order.order_lines = order_lines
        shipping_price = get(data, "costs.shipment.incVat", None)  # Expected to return a float
        if shipping_price:
            ship_ol = OrderLine()
            ship_ol.price = shipping_price
            ship_ol.vat = get(data, "costs.shipment.vat", 0)
            ship_ol.title = get(data, f"delivery.method.{lang}", "") or "Shipping"
            order.shipping_line = ship_ol

    if not order.order_lines:
        raise ValueError("No order-lines created, won't proceed.")  # Early validation

    email = get(data, "email", "") or get(data, "customer.info.email", "")
    if email:  # Only set email if non-empty, e.g. can't update to unset email
        # This looks for users with primary email, with secondary emails in identities and in auth_keys
        # (only used by old users that haven't upgraded yet)
        realname = get(data, "shippingName", "")
        if not realname:
            firstName = get(data, "customer.address.firstName", "")
            lastName = get(data, "customer.address.lastName", "")
            if firstName or lastName:
                realname = firstName + f" {lastName}" if lastName else ""
        user, created = user_from_email(email, realname=realname, create=create, commit=commit)
        if not user:
            raise ValueError(f"User with email {user} not found, can't create order")
        if created and job:
            job.info(f"Created new user from email {email}")
        order.user = user
        # Intentionally set to the email used for import, which may not be the default email for user
        order.email = email

    # If we have a paymentStatus and an email, we mark it as paid, otherwise as ordered
    status = get(data, "status", None)
    deliveryStatus = get(data, "deliveryStatus", None)
    paymentStatus = get(data, "paymentStatus", None)
    pledgedStatus = get(data, "pledgedStatus", None)
    if status in OrderStatus.keys():
        order.status = status
    elif order.email and deliveryStatus == "sent":
        order.status = OrderStatus.shipped
    elif order.email and (paymentStatus == "paid" or paymentStatus == "reserved" or pledgedStatus == "collected"):
        # TODO currently treating Abicart reserved as paid
        order.status = OrderStatus.paid
    elif deliveryStatus == "unsent" or paymentStatus == "unpaid":
        if paymentStatus == "unpaid":
            order.status = OrderStatus.ordered
        elif deliveryStatus == "unsent":
            order.status = OrderStatus.paid
    elif not (deliveryStatus or paymentStatus or pledgedStatus) and (
        not order.status or order.status == OrderStatus.cart
    ):
        # We have no input at all and current order is set to defaults
        # Assume we want to set status as ordered or paid
        order.status = OrderStatus.paid if (order.email and paymentStatus != "unsent") else OrderStatus.ordered

    ordered = (
        parse_datetime(get(data, "ordered", None))
        or parse_datetime(get(data, "created", None))
        or parse_datetime(get(data, "pledgedAt", None))
    )
    if ordered is not None:
        order.created = ordered

    source_url = get(data, "sourceUrl", None)
    if source_url:
        order.source_url = source_url

    message = get(data, "message", None)
    if message:
        order.message = message

    if commit:
        order.save()
        if order.user and (
            not is_updating or "order_fields" in order._changed_fields or "shipping_line" in order._changed_fields
        ):
            # We might have affected the total price, and need to create or regenerate a new Event
            ev = Event.objects(resource=order).first()
            if not ev:
                ev = Event()
            ev.action = "purchase"
            ev.user = order.user
            ev.resource = order
            ev.metric = order.total_price_sek()
            ev.created = order.created
            ev.save()
            order.user.save()  # Recalculates XP

    return order


def job_import_product(job, data, **kwargs):
    if "publisher" not in data and "publisher" in job.context:
        data["publisher"] = job.context["publisher"]

    return import_product(data, job=job, commit=not job.is_dry_run, **kwargs)


def import_product(data, job=None, commit=False, create=True, if_newer=True):
    """
    Updating modes:
    - Disallow any updating (only add new items)
    - Put (replace completely).
    - If newer (replace if newer)
    - (Patch isn't supported as it's the same as reducing the input data to only what's changed)

    Arguments:
        data {[type]} -- [description]

    Keyword Arguments:
        job {[type]} -- [description] (default: {None})
        commit {bool} -- [description] (default: {False})
        create {bool} -- [description] (default: {True})
        update {bool} -- [description] (default: {True})

    Raises:
        ValueError: [description]
        ValueError: [description]
        ValueError: [description]

    Returns:
        [type] -- [description]
    """
    # TODO, if we want to "PATCH" an instance, by providing key and selected data fields, we have to
    # check we don't create default values for other fields that overwrite the old data

    draft = get(data, "draft", None)
    if draft is not None and draft is True:
        if job:
            job.warn(f"Product {data} is marked as draft")
        return None

    # A product is identified by a unique article number
    artNo = get(data, "articleNumber", None) or get(data, "productNumber", None)
    if not artNo:
        if job:
            job.warn("Missing product number from this import, can't proceed")
        return None

    product = Product.objects(product_number=artNo).first()
    if product:
        is_updating = True  # We are patching an existing object
        # There is an existing product
        if if_newer:
            # Only update if newer
            changed = (
                parse_datetime(get(data, "changed", None))
                or parse_datetime(get(data, "updated", None))
                or parse_datetime(get(data, "imported", None))
            )
            if not changed:
                if job:
                    job.warn("Couldn't get valid changed/updated time from input data to decide to update the data")
                return None
            # We expect both datetimes to be in UTC. But Python might still have created them as timezone naive dt-objects.
            if changed.replace(tzinfo=None) <= product.updated:
                if job:
                    job.success = JobSuccess.SKIP
                return None  # Skip if we have already
    else:
        is_updating = False  # We are creating a new object from scratch
        product = Product(product_number=artNo)

    publisher = get(data, "publisher", None)
    if publisher:
        product.publisher = Publisher.objects(slug=publisher).first()
    if not product.publisher and not is_updating:  # Early validation to stop if no publisher
        raise ValueError("A publisher slug/domain is required when importing.")

    # Ignore hidden for the moment, for the most part, we want products to be visible in Lore
    # hidden = get(data, "hidden", None)
    # if hidden is True:
    #     product.status = ProductStatus.hidden
    # elif hidden is False:
    #     product.status = ProductStatus.available
    stock = get(data, "stock", "")
    if stock and stock.get("useStock", False) and stock.get("stock", None) == 0:
        product.status = ProductStatus.out_of_stock

    status = get(data, "status", "")
    if status and status in ProductStatus:
        product.status = status

    # Merges what we can read with the default string data, in overriding towards right
    title = get(data, f"name", None) or parse_i18n_field(data, "title")
    if title:
        product.title_i18n = {**default_translated_strings, **product.title_i18n, **title}

    desc = get(data, f"description", {})
    intro = get(data, f"introductionText", {})

    if intro or desc:
        content = {}
        for key in intro.keys() | desc.keys():
            content[key] = f"{html2text(intro.get(key, ''))}\n\n{html2text(desc.get(key, ''))}".strip()
    else:
        content = parse_i18n_field(data, "content")
    if content:
        product.description_i18n = {**default_translated_strings, **product.description_i18n, **content}

    shop_urls = get(data, f"url", None)
    if shop_urls is not None:
        product.shop_url_i18n = {**default_translated_nones, **product.shop_url_i18n, **shop_urls}
        # Can't allow empty URLs to be saved, but still, we want to be able to delete the previous URL
        # by setting it empty from import
        for key in product.shop_url_i18n.keys():
            if not product.shop_url_i18n[key]:
                del product.shop_url_i18n[key]

    prices = get(data, "price.regular", {}) or parse_price(get(data, "prices", ""))

    price_objects = []
    for currency in prices:
        if currency.lower() in Currencies and prices[currency] >= 0:
            price_objects.append(Price(price=prices[currency], currency=currency.lower()))
    if price_objects:
        product.prices = price_objects
        vatRate = get(data, "vatRate", product.tax)
        if isinstance(vatRate, str):
            vatRate = float("0" + vatRate)  # Small trick that makes a blank string into a float 0
        product.tax = vatRate

    created = parse_datetime(get(data, "created", None))
    if created:
        product.created = created

    product_type = get(data, "type", "").lower()
    if product_type and product_type in ProductTypes:
        product.type = product_type
    elif not product.type and "weight" or "freeFreight" in data:
        product.type = (
            ProductTypes.digital
            if get(data, "weight", 0) <= 1 and get(data, "freeFreight", False)
            else ProductTypes.book
        )

    # Guess more about type and status
    no_stock_pattern = re.compile(
        r"[\s([]*(slutsåld|slutsålt|ej tillgänglig|sold out|out of print)[\s)\]]*", re.IGNORECASE
    )

    if product.status is not ProductStatus.out_of_stock and no_stock_pattern.search(
        "".join(product.title_i18n.values())
    ):
        for lang in product.title_i18n.keys():
            product.title_i18n[lang] = no_stock_pattern.sub("", product.title_i18n[lang])
        if job:
            job.info("Guessed product.stats as Out of stock based on title")
        product.status = ProductStatus.out_of_stock
    if product.status is not ProductTypes.digital and re.search(
        "pdf|digital", "".join(product.title_i18n.values()), re.IGNORECASE
    ):
        if job:
            job.info("Guessed product.type as digital based on title")
        product.type = ProductTypes.digital
    elif product.status is not ProductTypes.shipping and re.search(
        "frakt|shipping", "".join(product.title_i18n.values()), re.IGNORECASE
    ):
        if job:
            job.info("Guessed product.type as shipping based on title")
        product.type = ProductTypes.shipping

    # Checks for a URL that looks like http://publisher.com/world_slug/...
    world_slug = get(data, "world", "") or extract(get(data, f"url.en", ""), r"helmgast.se/en/([^/]+)", default="")
    if world_slug:
        world = World.objects(slug=world_slug).first()
        if world:
            product.world = world
        elif job:
            job.warn(f"Couldn't find world with slug {world_slug}")

    slug_prefix = product.slug_path()

    image_urls = get(data, "images", None)
    if image_urls is not None:
        product.images = parse_url_assets(image_urls, product, commit, slug_prefix)
        if product.images:
            product.feature_image = product.images[0]

    dl_urls = get(data, "downloads", None)
    if dl_urls is not None:
        product.downloads = parse_url_assets(dl_urls, product, commit, slug_prefix, True)

    if commit:
        product.save()

    return product
