import unittest

from flask_mongoengine.wtf.models import ModelForm
from flask_mongoengine.wtf import model_form

# Below 3 lines needed to be able to access fablr module
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from fablr.app import create_app
from flask_mongoengine import Document
from mongoengine import EmbeddedDocument, StringField
from werkzeug.datastructures import ImmutableMultiDict


# Find good set of dummy / dangerous data to populate with, e.g. special chars,
# html, scripts, etc

# What to test
# Password login
# Google login
# Facebook login
# Remind password (email received?)
# Logout
# Access (is an admin, gets admin)
# Access (is a user, dont get admin)
# Register user, user exist
# Register user, email sent
# Password length
# Username length and contents
# 404 - generate and test all URLs?
# User can change password
# User cannot change other user password
# That PDF fingerprinting works, test some different PDFs

# requests
# test adding new args
# test adding evil args
# test defaults of args, e.g. per_page
# test intent and method
# test naming articles put, post, patch, etc
# test naming articles the same

# World
# test title less than or larger than allowed length
# test difficult slug
# test incorrect status choice

# FileTests
# - find list of files to test
# - upload files with wrong file end
# - upload files with right file, wrong mine
# - upload with weird (Unicode) file name
# - upload with same name as previous

class CSRFDisabledModelForm(ModelForm):
    def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
        super(CSRFDisabledModelForm, self).__init__(formdata, obj, prefix, csrf_enabled=False, **kwargs)


class TestObject(Document):
    name = StringField(max_length=60)


class FablrTestCase(unittest.TestCase):
    def test_forms2(self):
        from fablr.model.shop import Order, OrderLine
        from fablr.controller.resource import RacBaseForm, RacModelConverter
        from flask_mongoengine.wtf import model_form
        from wtforms.fields import FormField
        from fablr.controller.shop import FixedFieldList, CartForm
        CartOrderLineForm = model_form(OrderLine, only=['quantity', 'comment'], base_class=RacBaseForm,
                                       converter=RacModelConverter())

        class CartForm(RacBaseForm):
            order_lines = FixedFieldList(FormField(CartOrderLineForm))

        obj = Order(email='test@test.com', order_lines=[
            OrderLine(product='a' * 12, price=1, quantity=1, comment=''),
            OrderLine(product='b' * 12, price=1, quantity=2, comment=''),
            OrderLine(product='c' * 12, price=1, quantity=3, comment='')
        ])
        formdata = ImmutableMultiDict({
            'email': 'test@test.com',  # Removed first order line item, index -0-
            'order_lines-1-quantity': '2',
            'order_lines-1-comment': '',
            'order_lines-2-quantity': '3',
            'order_lines-2-comment': ''
        })
        # Object which has the 2nd and 3rd OrderLine from above object
        expected_obj = Order(email='test@test.com', order_lines=[
            OrderLine(product='b' * 12, price=1, quantity=2, comment=''),
            OrderLine(product='c' * 12, price=1, quantity=3, comment='')
        ])
        form = CartForm(formdata, obj=obj)
        form.populate_obj(obj)
        print "Obj1 \n%s\n" % obj.to_mongo()
        #   print "Obj2 \n%s\n" % obj2.to_mongo()
        self.assertEqual(expected_obj.to_mongo(), obj.to_mongo())

    def test_strategy_simple(self):
        strategy = self.ResourceRoutingStrategy(TestObject, 'test_objects', short_url=True)
        # Test that a strategy correctly sets up url routes
        self.assertEqual('/test_objects/', strategy.url_list())
        self.assertEqual('/test_objects/new', strategy.url_list('new'))
        self.assertEqual('/<testobject>/', strategy.url_item())
        self.assertEqual('/<testobject>/edit', strategy.url_item('edit'))
        self.assertEqual('testobject_item.html', strategy.item_template())
        self.assertEqual('testobject_list.html', strategy.list_template())
        self.assertEqual('testobject_view', strategy.endpoint_name('view'))

    def test_strategy_query(self):
        strategy = self.ResourceRoutingStrategy(TestObject, 'test_objects', short_url=True)
        obj = TestObject(name="test_name").save()
        self.assertIn(obj, strategy.query_list({"name": "test_name"}))
        self.assertEqual(0, len(strategy.query_list({"name": "test_name_1"})))
        self.assertEqual(1, len(strategy.query_list({"name_1": "test_name"})))
        self.assertEqual({}, strategy.query_parents(**{"name": "test_name"}))
        self.assertAlmostEqual(type(TestObject()), type(strategy.create_item()))
        self.assertEqual({'testobject': None}, strategy.all_view_args(TestObject()))

    def test_handler(self):
        strategy = self.ResourceRoutingStrategy(TestObject, 'test_objects',
                                                form_class=model_form(TestObject))
        handler = self.ResourceHandler(strategy)
        handler.register_urls(self.app, strategy)
        with self.app.test_request_context(path='/test_objects/new', method="POST", data={"name": "test_name_handler"}):
            self.app.preprocess_request()  # Correctly sets up auth, etc
            result = handler.new({'op': 'new'})
            self.assertEqual('new', result['op'])
            self.assertEqual(u'test_name_handler', result['item'].name)

    def login(self, username, password):
        return self.client.post('/accounts/login/', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/accounts/logout', follow_redirects=True)

    def setUp(self):
        # PRESERVE_CONTEXT... needed for avoiding context pop error, see
        # http://stackoverflow.com/questions/26647032/py-test-to-test-flask-register-assertionerror-popped-wrong-request-context
        # WTF_CSRF_CHECK_DEFAULT turn off all CSRF, test that in specific case only
        self.app = create_app(TESTING=True, PRESERVE_CONTEXT_ON_EXCEPTION=False, WTF_CSRF_CHECK_DEFAULT=False)
        self.client = self.app.test_client()
        # we need to fix imports here because the need app data at load time
        from fablr.controller.resource import ResourceRoutingStrategy, ResourceHandler, RacBaseForm
        self.ResourceRoutingStrategy = ResourceRoutingStrategy
        self.ResourceHandler = ResourceHandler
        self.RacBaseForm = RacBaseForm
        TestObject.drop_collection()  # Ensure clean slate

    def tearDown(self):
        pass
        # TestObject.drop_collection()
        # os.close(self.db_fd)
        # os.unlink(app.the_app.config['DATABASE'])


def run_tests():
    unittest.main()


if __name__ == '__main__':
    unittest.main()
