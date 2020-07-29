import pytest
import json
import responses
from datetime import datetime

from lore.model.user import Event, User
from lore.model.shop import Order, OrderLine, import_order, import_product, FX_IN_SEK
from tools.import_sheets import to_camelcase

# TESTS TO DO

# Test mismatch in language or currencies e.g within orderlines

# Test updating that doesn't overwrite unneccesarily

# Test too long titles making too long slugs

# Test corner cases on internationalized fields, like empty strings, new keys, etc.

# Test internationalization with mocked configured_locales (currently would be empty)


@pytest.fixture()
def db_loaded_product_data(app_client):
    from lore.model.shop import Product, ProductTypes
    from lore.model.world import Publisher, World

    pub = Publisher(slug="helmgast.se", title="Helmgast AB")
    pub2 = Publisher(slug="otherpub.com", title="OtherPub")
    p1 = Product(
        product_number="KDL-132", title_i18n={"en": "Rockets Red Glare"}, publisher=pub, type=ProductTypes.digital
    )
    p2 = Product(product_number="KDL-121l", title_i18n={"en": "T-shirt"}, publisher=pub, type=ProductTypes.item)
    p3 = Product(product_number="EON-808", title_i18n={"en": "Strid Helmgast"}, publisher=pub, type=ProductTypes.book)
    p4 = Product(product_number="EON-080", title_i18n={"en": "Strid"}, publisher=pub, type=ProductTypes.book)
    w1 = World(slug="neotech", title="Neotech", publisher=pub)

    with app_client.application.test_request_context():
        pub.save()
        p1.save()
        p2.save()
        p3.save()
        p4.save()
        w1.save()
    return {"hg_pub": pub, "kdl-132": p1, "kdl-121l": p2, "eon-808": p3, "eon-080": p4, "neotech": w1}


def test_basic_import_order(mongomock, app_client, db_loaded_product_data):
    o = import_order(
        {"key": "a", "orderLines": "KDL-132|KDL-121l|Random title#comment@12*0.25\nJust a message", "publisher": "helmgast.se", "currency": "sek"}, commit=True
    )
    # An order can be separated in lines by either | or line feed
    assert o.external_key == "a"
    assert o.order_lines[0].product.product_number == "KDL-132"
    assert o.order_lines[1].product.product_number == "KDL-121l"
    assert o.order_lines[2].title == "Random title"
    assert o.order_lines[2].price == 12.0
    assert o.order_lines[2].comment == "comment"
    assert o.order_lines[2].vat == Order.calc_vat(12.0, 0.25)
    assert o.order_lines[3].title == "Just a message"
    assert o.order_lines[3].price is None


def test_basic_error_import_order(mongomock, app_client, db_loaded_product_data):
    # Test with Product and User already in DB, and without

    assert import_order(None) is None  # Expect a warning if we had a job

    assert import_order({"nokey": "a", "orderLines": "KDL-132", "publisher": "helmgast.se"}) is None  # No key

    with pytest.raises(ValueError):
        # No order lines
        import_order({"key": "a", "orderLines": "", "publisher": "helmgast.se"})


@pytest.fixture
def textalk_order():
    # Imports a JSON representing an Order object.
    # References to OrderItems has been replaced with actual OrderItem data.
    with open("tests/testdata/textalk_order.json") as f:
        data = json.load(f)

    # Enhance data with global options as we would at actual import
    data["publisher"] = "helmgast.se"
    data["title"] = "Webshop"
    return data


@pytest.fixture
def textalk_product():
    # Imports a JSON representing a Product object.
    with open("tests/testdata/textalk_product.json") as f:
        data = json.load(f)

    # Enhance data with global options as we would at actual import
    data["publisher"] = "helmgast.se"
    return data


def test_textalk_order_import(mongomock, app_client, db_loaded_product_data, textalk_order):

    order = import_order(textalk_order, commit=True)
    assert order.external_key == str(textalk_order["uid"])
    # To be efficient, we have only populated order.publisher with id, not full de-referenced object
    assert order.publisher == db_loaded_product_data["hg_pub"]
    assert textalk_order["customer"]["info"]["email"] in order.user.identities_by_email()
    assert order.email == textalk_order["customer"]["info"]["email"]
    assert order.user.realname == "FirstName LastName"
    assert order.created.replace(tzinfo=None) == datetime(2020, 4, 17, 11, 54, 44)  # 2020-04-17T11:54:44Z
    assert order.total_price == textalk_order["costs"]["total"]["incVat"]
    assert order.currency == textalk_order["currency"].lower()
    assert order.title == textalk_order["title"]
    assert order.shipping_line.price == textalk_order["costs"]["shipment"]["incVat"]

    ev = Event.objects(resource=order).first()
    assert ev is not None
    assert ev.xp == int(textalk_order["costs"]["total"]["incVat"] * FX_IN_SEK['eur'])

    # Check that a re-import of similar data, same key, will update the existing order object with new data
    textalk_order["title"] = "New title"
    order2 = import_order(textalk_order, commit=True, if_newer=False)
    order_from_db = Order.objects(id=order.id).get()
    assert order_from_db.title == textalk_order["title"]
    assert order_from_db.updated > order.updated


def test_textalk_order_import_discarded(mongomock, app_client, db_loaded_product_data, textalk_order):
    textalk_order["discarded"] = True

    assert import_order(textalk_order, commit=True) == None  # Expect to skip discarded


def test_textalk_order_import_wrong_items(mongomock, app_client, db_loaded_product_data, textalk_order):
    textalk_order["items"] = [123123, 42132]  # How items may look if we failed to replace with OrderItems

    with pytest.raises(Exception):  # Can be KeyError
        order = import_order(textalk_order, commit=True)


def test_textalk_order_import_no_discount(mongomock, app_client, db_loaded_product_data, textalk_order):
    del textalk_order["items"][0]["discountInfo"]  # Not all orders have discountInfo

    order = import_order(textalk_order, commit=True)
    assert order.order_lines[0].price == textalk_order["items"][0]["costs"]["total"]["incVat"]


def test_textalk_order_import_no_shipping(mongomock, app_client, db_loaded_product_data, textalk_order):
    del textalk_order["delivery"]  # Not all orders have shipping
    del textalk_order["costs"]["shipment"]

    order = import_order(textalk_order, commit=True)
    assert order.total_price == textalk_order["costs"]["cart"]["incVat"]  # Cart is price without shipping


def test_textalk_order_import_unkown_publisher(mongomock, app_client, db_loaded_product_data, textalk_order):
    textalk_order["publisher"] = "frialigan.se"

    with pytest.raises(Exception):  # Can be KeyError
        order = import_order(textalk_order, commit=True)


def test_textalk_order_import_unkown_products(mongomock, app_client, db_loaded_product_data, textalk_order):
    textalk_order["items"][0]["articleNumber"] = "XXX-000"  # Incorrect article number

    with pytest.raises(Exception):  # Can be KeyError
        order = import_order(textalk_order, commit=True)


def test_textalk_order_import_unkown_user(mongomock, app_client, db_loaded_product_data, textalk_order):
    assert User.objects().count() == 0  # db_loaded_product_data currently comes with zero users

    with pytest.raises(Exception):  # Expect error as we aren't allowed to create user
        order = import_order(textalk_order, commit=True, create=False)


def test_textalk_import_create_user(mongomock, app_client, db_loaded_product_data, textalk_order):
    assert User.objects().count() == 0  # db_loaded_product_data currently comes with zero users

    order = import_order(textalk_order, commit=True, create=True)
    assert User.objects().first().id == order.user.id


def test_textalk_order_update(mongomock, app_client, db_loaded_product_data, textalk_order):
    # Test that when input is partial, we only touch those fields and don't overwrite other fields with defaults

    original_order = import_order(textalk_order, commit=True)  # Import it so it exists in DB

    uid = textalk_order["uid"]

    changed = {"uid": uid, "customer": {"info": {"email": "user2@email.com",}}}
    new_order = import_order(changed, commit=False, if_newer=False)
    assert set(new_order._changed_fields) == {"user", "email"}

    changed = {"uid": uid, "currency": "SEK"}
    new_order = import_order(changed, commit=False, if_newer=False)
    assert set(new_order._changed_fields) == {"currency"}

    changed = {"uid": uid, "items": [textalk_order["items"][0]]}
    new_order = import_order(changed, commit=False, if_newer=False)
    assert set(new_order._changed_fields) == {"order_lines"}

    changed = {"uid": uid, "deliveryStatus": "unsent"}
    new_order = import_order(changed, commit=False, if_newer=False)
    assert set(new_order._changed_fields) == {"status"}

    changed = {"uid": uid, "ordered": "2020-04-18T16:17:04Z"}
    new_order = import_order(changed, commit=False, if_newer=False)
    assert set(new_order._changed_fields) == {"created"}

    new_order.save()
    assert new_order.updated > original_order.updated


@pytest.fixture
def kickstarter_order():

    data = {
        "Backer Number": "1",
        "Backer UID": "1647400540",
        "Backer Name": "First Last",
        "Email": "first.last@gmail.com",
        "Shipping Country": "SE",
        "Shipping Amount": "SEK 100.00",
        "Reward Title": "Basare",
        "Reward Minimum": "SEK 650.00",
        "Reward ID": "6526680",
        "Pledge Amount": "SEK 1,000.00",
        "Pledged At": "2018/03/28, 10:27",
        "Rewards Sent?": "",
        "Pledged Status": "collected",
        "Notes": "",
        "Billing State/Province": "",
        "Billing Country": "SE",
        "Survey Response": "2018/05/26, 14:05",
        "Shipping Name": "First Last",
        "Shipping Address 1": "Street 15 Lgh 1302",
        "Shipping Address 2": "",
        "Shipping City": "Tyresö",
        "Shipping State": "Stockholms Län",
        "Shipping Postal Code": "135 44",
        "Shipping Country Name": "Sweden",
        "Shipping Country Code": "SE",
        "Shipping Phone Number": "",
        "Shipping Delivery Notes": "",
        "Order Lines": "2xEON-808|EON-080|3xKDL-121l@19.9*0.25|Sticker",  # Order Lines is not provided by Kickstarter, need to be added by us
        "Publisher": "helmgast.se",  # Publisher need to be added by us at import
        "Title": "Neotech Edge Kickstarter",  # Title need to be added by us at import
        "Key": "KS-NEOTECH-1",  # external_key should be set from Backer UID and Reward ID to be unique.
        "Extra Emailadress": "other@email.com",
        "Delivery Method": "Sverigefrakt",
        "VAT Rate": "0.06",  # Applies to the reward line
    }
    # When importing we will always do camelCase keys
    return {to_camelcase(k): v for k, v in data.items()}


def test_ks_order_import(mongomock, app_client, db_loaded_product_data, kickstarter_order):

    order = import_order(kickstarter_order, commit=True)

    assert order.external_key == "KS-NEOTECH-1"
    assert order.publisher == db_loaded_product_data["hg_pub"]
    assert order.email == kickstarter_order["email"]
    assert order.user.realname == "First Last"

    # https://stackoverflow.com/questions/19654578/python-utc-datetime-objects-iso-format-doesnt-include-z-zulu-or-zero-offset

    assert order.created.replace(tzinfo=None) == datetime(2018, 3, 28, 10, 27, 0, 0)  # 2018/03/28, 10:27
    assert order.currency == "sek"
    assert order.title == "Neotech Edge Kickstarter: Basare"

    # First line should be the reward
    assert order.order_lines[0].quantity == 1
    assert order.order_lines[0].title == "Basare"
    assert order.order_lines[0].price == 650.0
    assert order.order_lines[0].vat == pytest.approx(650 * 0.06 / 1.06, 0.001)

    assert order.order_lines[1].quantity == 2
    assert order.order_lines[1].product == db_loaded_product_data["eon-808"]
    assert order.order_lines[1].price is None  # Expect no price as it counts as part of reward when no price given
    assert order.order_lines[1].vat is None

    assert order.order_lines[2].quantity == 1
    assert order.order_lines[2].product == db_loaded_product_data["eon-080"]
    assert order.order_lines[2].price is None  # Expect no price as it counts as part of reward when no price given
    assert order.order_lines[2].vat is None

    assert order.order_lines[3].quantity == 3
    assert order.order_lines[3].product == db_loaded_product_data["kdl-121l"]
    assert order.order_lines[3].price == 19.9 * 3  # Expect no price as it counts as part of reward when no price given
    assert order.order_lines[3].vat == pytest.approx(19.9 * 3 * 0.25 / 1.25, 0.001)

    assert order.order_lines[4].quantity == 1
    assert order.order_lines[4].product is None
    assert order.order_lines[4].title == "Sticker"
    assert order.order_lines[4].price is None
    assert order.order_lines[4].vat is None

    assert order.order_lines[5].quantity == 1
    assert order.order_lines[5].product is None
    assert order.order_lines[5].title == "Extra pledge"
    assert order.order_lines[5].price == 1000 - 650 - 100 - 3 * 19.9  # 190.3
    assert order.order_lines[5].vat == 0

    assert order.shipping_line.quantity == 1
    assert order.shipping_line.title == "Sverigefrakt"
    assert order.shipping_line.price == 100.0
    # Here we check a correctly calculated VAT for shipping with mixed VAT products
    # Reference https://support.fortnox.se/hc/sv/articles/208332015-Momssatser-p%C3%A5-frakt-och-expeditionsavgifter
    # We calculate average vatRate by multiplyig each price with its vatRate and then divide by total price (all before adding shipping)
    shipping_vat_rate = (650 * 0.06 + 3 * 19.9 * 0.25) / (1000 - 100)
    assert order.shipping_line.vat == pytest.approx(
        100 - 100 / (1 + shipping_vat_rate), 0.001
    )  # Extra pledege is at VAT 0 so not counted

    assert order.total_price == 1000.0
    assert len(order.order_lines) == 6  # reward line plus four products plus extra pledge
    assert order.total_items == 9  # 1 reward, 2 EON-808, 1 EON-080, 3 KDL-121, 1 Sticker, 1 extra pledge


def test_ks_order_update(mongomock, app_client, db_loaded_product_data, kickstarter_order):

    original_order = import_order(kickstarter_order, commit=True)  # Import it so it exists in DB

    key = kickstarter_order["key"]

    changed = {"key": key, "email": "user2@email.com"}
    new_order = import_order(changed, commit=False, if_newer=False)
    assert set(new_order._changed_fields) == {"user", "email"}

    changed = {"key": key, "orderLines": "Name in book@10*0"}
    new_order = import_order(changed, commit=False, if_newer=False)
    assert set(new_order._changed_fields) == {"order_lines"}

    changed = {"key": key, "title": "Other KS"}
    new_order = import_order(changed, commit=False, if_newer=False)
    assert set(new_order._changed_fields) == {"title"}

    # Currently can't update just shipping price without new orderlines
    # changed = {"key": key, "deliveryMethod": "Global", "shippingPrice": "sek 40"}
    # new_order = import_order(changed, commit=False, if_newer=False)
    # assert set(new_order._changed_fields) == {"shipping_line"}

    new_order.save()
    assert new_order.updated > original_order.updated

def test_orderline(mongomock, app_client, db_loaded_product_data):
    order = Order()
    order.order_lines = []
    order.order_lines.append(OrderLine(title="Test", price=10, vat=2))
    order.order_lines.append(OrderLine(product=db_loaded_product_data["kdl-132"]))
    order.save()
    o_json = order.to_json()
    o_str = str(order)
    print(o_json, o_str)


mock_urls = {
    "google_png": responses.Response(
        method='GET',
        url="https://drive.google.com/uc?export=view&id=1zrZTkPr5BxLSrNdg9dwvOLoVDLkR_tOO",
        content_type="image/png",
        headers={
            "Content-Disposition": 'attachment;filename="anon_2d-1200px.png";filename*=UTF-8' "anon_2d-1200px.png",
            "content-range": "bytes 0-100/767041",
        }
    ),
    "google_pdf": responses.Response(
        method='GET',
        url="https://drive.google.com/uc?export=view&id=1tiK06Lhwe66Wi8SRvYHgXvGMoGnw9fWs",
        content_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment;filename="Aspekt_biotropi.pdf";',
            "content-range": "bytes 0-100/767041",
        }
    ),
    "textalk_png1": responses.Response(
        method='GET',
        url="https://shopcdn.textalk.se/shop/ws51/49251/art51/h1595/171461595-origpic-dc1758.png",
        content_type="image/png"
    ),
    "textalk_png2": responses.Response(
        method='GET',
        url="https://shopcdn.textalk.se/shop/ws51/49251/art51/h1595/171461595-origpic-15fa6c.png",
        content_type="image/png"
    )
}

def test_textalk_product_import(mongomock, app_client, db_loaded_product_data, textalk_product, mocked_responses):

    # Set up mocked responses to request, for faster test and reproducibility
    mocked_responses.add(mock_urls["google_png"])
    mocked_responses.add(mock_urls["textalk_png1"])
    mocked_responses.add(mock_urls["textalk_png2"])

    textalk_product["images"][0] = mock_urls["google_png"].url
    product = import_product(textalk_product, commit=True)

    assert product.product_number == textalk_product["articleNumber"]
    assert product.publisher == db_loaded_product_data["hg_pub"]
    assert product.title_i18n["en"] == "Neotech Edge Pearl River Delta"  # Removed SOLD OUT tag
    assert product.world.slug == "neotech"
    for price in product.prices:
        assert price.currency.upper() in textalk_product["price"]["regular"].keys()
        assert price.price == textalk_product["price"]["regular"][price.currency.upper()]

    # https://stackoverflow.com/questions/19654578/python-utc-datetime-objects-iso-format-doesnt-include-z-zulu-or-zero-offset
    assert product.created.replace(tzinfo=None) == datetime(2019, 10, 21, 21, 15, 31, 0)

    # TODO test description
    assert product.status == "out_of_stock"  # Guessed from the title heuristics

    # Attempt to re-import
    # product = import_product(textalk_product, commit=True)

    # Check that a re-import of similar data, same key, will update the existing order object with new data
    # textalk_order["title"] = "New title"
    # order2, *_ = import_order(textalk_order, commit=True)
    # order_from_db = Order.objects(id=order.id).get()
    # assert order_from_db.title == textalk_order["title"]
    # assert order_from_db.updated > order.updated


def test_textalk_product_update(mongomock, app_client, db_loaded_product_data, textalk_product, mocked_responses):
    mocked_responses.add(mock_urls["google_png"])
    mocked_responses.add(mock_urls["textalk_png1"])
    mocked_responses.add(mock_urls["textalk_png2"])

    textalk_product["images"][0] = mock_urls["google_png"].url
    # To cover more variation, remove SOLD OUT from title, to ensure we also get available status
    textalk_product["name"] = {
      "en": "Neotech Edge Pearl River Delta",
      "sv": "Neotech Edge Pearl River Delta"
    }

    product = import_product(textalk_product, commit=True)
    assert product.status == "available"  # No out of stock in title anymore

    pnum = textalk_product["articleNumber"]

    changed = {"articleNumber": pnum, "images": [mock_urls["textalk_png1"].url]}
    updated_product = import_product(changed, commit=False, if_newer=False)
    assert set(updated_product._changed_fields) == {"images", "feature_image"}


def test_textalk_product_outofstock(mongomock, app_client, db_loaded_product_data, textalk_product, mocked_responses):
    mocked_responses.add(mock_urls["google_png"])
    mocked_responses.add(mock_urls["textalk_png1"])
    mocked_responses.add(mock_urls["textalk_png2"])

    textalk_product["images"][0] = mock_urls["google_png"].url
    textalk_product["name"] = {
      "en": "Neotech Edge Pearl River Delta",
      "sv": "Neotech Edge Pearl River Delta"
    }

    textalk_product["stock"]["useStock"] = True
    product = import_product(textalk_product, commit=True)
    assert product.status == "out_of_stock"



@pytest.fixture
def sheets_product():

    data = {
        "Product Number": "ABC-123",
        "Created": "2018/10/16, 09:00",
        "Updated": "2019-04-23T21:24:27Z",
        "Status": "out_of_stock",
        "Publisher": "helmgast.se",
        "Type": "book",
        "Title:en": "A great book",
        "Content:en": "Really, really great. Almost perfect.",
        "Title:sv": "Riktigt bra bok",
        "Content:sv": "Bra som tusan, må jag säga",
        "Prices": "SEK 1,750.50",
        "VAT Rate": "0.06",
        "World": "neotech",
        "Images": """https://shopcdn.textalk.se/shop/ws51/49251/art51/h1595/171461595-origpic-dc1758.png | 
        https://shopcdn.textalk.se/shop/ws51/49251/art51/h1595/171461595-origpic-15fa6c.png""",
        "Downloads": """Aspekt Biotropi.pdf https://drive.google.com/uc?export=download&id=1tiK06Lhwe66Wi8SRvYHgXvGMoGnw9fWs | 
        Anon (bild).png https://drive.google.com/file/d/1zrZTkPr5BxLSrNdg9dwvOLoVDLkR_tOO/view?usp=sharing""",
    }
    # When importing we will always do camelCase keys
    return {to_camelcase(k): v for k, v in data.items()}


def test_product_import(mongomock, app_client, db_loaded_product_data, mocked_responses, sheets_product):

    # Set up mocked responses to request, for faster test and reproducibility
    mocked_responses.add(mock_urls["google_png"])
    mocked_responses.add(mock_urls["google_pdf"])
    mocked_responses.add(mock_urls["textalk_png1"])
    mocked_responses.add(mock_urls["textalk_png2"])

    product = import_product(sheets_product, commit=True)

    assert product.product_number == sheets_product["productNumber"]
    assert product.publisher == db_loaded_product_data["hg_pub"]
    assert product.title_i18n["en"] == sheets_product["title:en"]
    assert product.title_i18n["sv"] == sheets_product["title:sv"]
    assert product.world.slug == "neotech"
    assert product.prices[0].currency == "sek"
    assert product.prices[0].price == 1750.5
    assert product.created.replace(tzinfo=None) == datetime(2018, 10, 16, 9, 0, 0, 0)
    assert (product.images[0].source_file_url == mock_urls["textalk_png1"].url)
    assert (product.downloads[0].source_file_url == mock_urls["google_pdf"].url)
    assert product.downloads[0].title == "Aspekt Biotropi.pdf"
    assert product.downloads[0].slug == "neotech/abc-123/aspekt_biotropi.pdf"
