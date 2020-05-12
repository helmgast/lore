import unittest

# Below 3 lines needed to be able to access lore module
import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

from lore.app import create_app
from flask_mongoengine import Document
from mongoengine import StringField
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


class TestObject(Document):
    name = StringField(max_length=60)


class LoreTestCase(unittest.TestCase):
    def test_forms2(self):
        from lore.model.shop import Order, OrderLine
        from lore.api.resource import ImprovedBaseForm, ImprovedModelConverter
        from flask_mongoengine.wtf import model_form
        from wtforms.fields import FormField
        from lore.api.shop import FixedFieldList
        CartOrderLineForm = model_form(OrderLine, only=['quantity', 'comment'], base_class=ImprovedBaseForm,
                                       converter=ImprovedModelConverter())

        class CartForm(ImprovedBaseForm):
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
        print("Obj1 \n%s\n" % obj.to_mongo())
        #   print "Obj2 \n%s\n" % obj2.to_mongo()
        self.assertEqual(
            expected_obj.to_mongo(), obj.to_mongo())

    def setUp(self):
        # PRESERVE_CONTEXT... needed for avoiding context pop error, see
        # http://stackoverflow.com/questions/26647032/py-test-to-test-flask-register-assertionerror-popped-wrong-request-context
        # WTF_CSRF_CHECK_DEFAULT turn off all CSRF, test that in specific case only
        self.app = create_app(TESTING=True, PRESERVE_CONTEXT_ON_EXCEPTION=False, WTF_CSRF_CHECK_DEFAULT=False)
        self.client = self.app.test_client()
        # we need to fix imports here because the need app data at load time
        from lore.api.resource import ResourceRoutingStrategy, ResourceHandler, ImprovedBaseForm
        self.ResourceRoutingStrategy = ResourceRoutingStrategy
        self.ResourceHandler = ResourceHandler
        self.ImprovedBaseForm = ImprovedBaseForm
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
