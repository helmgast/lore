from raconteur import db
from model.world import list_to_choices
from flask.ext.babel import lazy_gettext as _

PRODUCT_TYPES = list_to_choices(['Book', 'Item', 'Digital'])
PRODUCT_STATUS = list_to_choices([
	'Pre-order', 
	'Available', 
	'Out of stock',
	'Hidden'
	])
class Product(db.Document):
 	slug = db.StringField(unique=True, max_length=62) # URL-friendly name
 	title = db.StringField(max_length=60, required=True, verbose_name=_('Title'))
	publisher = db.StringField(max_length=60, required=True, verbose_name=_('Publisher'))
    family = db.StringField(unique=True, max_length=60, verbose_name=_('Family'))
    created = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
    type = db.StringField(choices=PRODUCT_TYPES, required=True, verbose_name=_('Type'))
    price = db.IntField(min_value=0, required=True, verbose_name=_('Price'))
    status = db.StringField(choices=PRODUCT_STATUS, default=PRODUCT_STATUS[3], verbose_name=_('Status'))

ORDER_STATUS = list_to_choices([
	'created',
	'paid',
	'shipped',
	'error'
	])
class Order(db.Document):
	user = db.ReferenceField(User, verbose_name=_('User'))
	email = db.EmailField(max_length=60, required=True, verbose_name=_('Email'))
	product = db.ReferenceField(Product, required=True, verbose_name=_('Product'))
    created = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Created'))
    updated = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Updated'))
	status = db.StringField(choices=ORDER_STATUS, default=ORDER_STATUS[0], verbose_name=_('Status'))