from typing import Dict
from itertools import product
import pytest
import base64
from werkzeug.routing import Rule
from flask import request, url_for, g
from flask.sessions import SecureCookieSessionInterface

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


@pytest.fixture()
def db_basic_data(app_client, mongomock):
    from lore.model.shop import Product, ProductTypes, Order, OrderLine
    from lore.model.world import Publisher, World, Article, ArticleTypes, Shortcut
    from lore.model.user import User
    from lore.model.asset import FileAsset

    with app_client.application.test_request_context():

        # Users
        u1 = User(email="test@test.com", logged_in=True, status="active").save()

        # Publishers
        pub = Publisher(slug="helmgast.se", title="Helmgast AB").save()
        pub2 = Publisher(slug="otherpub.com", title="OtherPub").save()

        # Worlds
        w1 = World(slug="neotech", title_i18n={"en": "Neotech"}, publisher=pub).save()

        # Articles
        a1 = Article(type=ArticleTypes.blogpost, title="Great blog post", publisher=pub2).save()
        a2 = Article(type=ArticleTypes.person, world=w1, title="Mr Neo", publisher=pub, creator=u1).save()

        # Shortcuts
        s1 = Shortcut(slug="abcdef", article=a2).save()
        s2 = Shortcut(slug="ghijkl", url="https://google.com").save()

        # Products

        p1 = Product(
            product_number="KDL-132", title_i18n={"en": "Rockets Red Glare"}, publisher=pub, type=ProductTypes.digital
        ).save()
        p2 = Product(
            product_number="KDL-121l", title_i18n={"en": "T-shirt"}, publisher=pub, type=ProductTypes.item
        ).save()
        p3 = Product(
            product_number="EON-808", title_i18n={"en": "Strid Helmgast"}, publisher=pub, type=ProductTypes.book
        ).save()
        p4 = Product(
            product_number="EON-080", title_i18n={"en": "Strid"}, publisher=pub, type=ProductTypes.book
        ).save()

        # Orders
        o1 = Order(
            user=u1, order_lines=[OrderLine(product=p4), OrderLine(quantity=2, product=p2), OrderLine(title="Gift")]
        ).save()
        o2 = Order(user=u1, order_lines=[OrderLine(product=p3)], external_key="test", publisher=pub).save()

        # Assets

        # Minimal PNG file as base64
        png = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HgAGgwJ/lK3Q6wAAAABJRU5ErkJggg=="

        f1 = FileAsset(slug="test/file.png", source_filename="file.png", content_type="image/png")
        f1.file_data.put(base64.b64decode(png), content_type="image/png")
        f1.save()

        return {"o1": o1, "u1": u1}


class FlaskRouteTester:
    def __init__(self, app_client, input_data: Dict, expected_results: Dict):
        self.app_client = app_client
        self.input_data = input_data
        self.expected_results = expected_results
        self.session_serializer = SecureCookieSessionInterface().get_signing_serializer(app_client.application)

    def iter_inputs(self, route: Rule):
        error = ""
        # prepare input
        filtered_keys = []
        filtered_input = []
        for k, v in self.input_data.items():
            if k not in route.arguments | {"accept", "method", "session.uid"}:
                continue
            if isinstance(v, dict):
                if route.endpoint in v:
                    v = v[route.endpoint]
                else:
                    v = None
                    error += f"{route.endpoint} not in input_data[{k}], "
            if not isinstance(v, list):
                v = [v]
            if k == "method":  # Filter methods to those available
                v = [m for m in v if m in route.methods]
            if v is not None:
                filtered_keys.append(k)
                filtered_input.append(v if isinstance(v, list) else [v])
        return map(lambda x: dict(zip(filtered_keys, x)), product(*filtered_input))

    def test_routes(self, expect_func, filter_func=None):
        tests = 0
        routes = filter(filter_func, self.app_client.application.url_map.iter_rules())
        for r in routes:
            input_variations = self.iter_inputs(r)
            for values in input_variations:
                reason = ""
                expected_status = expect_func(r.endpoint, values)
                method = values.pop("method", None)
                h = {"accept": values.pop("accept", "*/*")}
                sessionuid = values.pop("session.uid", None)
                if method:
                    if len(values) >= len(r.arguments):
                        url_parts = r.build(values)
                        if url_parts:
                            url = f"http://{url_parts[0]}{url_parts[1]}"
                            if sessionuid is not None:
                                h["Cookie"] = f"session={self.session_serializer.dumps({'uid': sessionuid})}"
                            rv = self.app_client.open(url, headers=h, method=method)
                            assert (
                                rv.status_code == expected_status
                            ), f"{method} failed {url} ({r.endpoint}, {h}, session={sessionuid})"
                            tests += 1
                            continue
                        else:
                            reason += "url build failed, "
                    else:
                        reason += "not enough args predefined, "
                else:
                    reason += "no supported method, "
                print(f"Route {r} [{r.endpoint}] not tested: {reason}")
        print(f"Tested {tests} route variations")


def test_all_routes(app_client, db_basic_data):
    # app_client.application.config["PRODUCTION"] = True
    h = {"accept": "*/*"}

    all_args = {
        "method": ["GET"],
        "accept": ["text/html", "application/json"],
        "session.uid": [str(db_basic_data["u1"].pk), None],
        "pub_host": "helmgast.se",
        "code": ["abcdef", "ghijkl"],
        "intent": [None, "patch"],
        "key": "test",
        "type": "image",
        "lang": "en",
        "slug": "test/file.png",
        "fileasset": "test/file.png",
        "mail_type": "compose",
        "world_": "neotech",
        "filename": {"plugins": "helmgast-theme/logo-helmgast.svg", "static": "img/icon/favicon.ico"},
        "id": {
            "world.ArticlesView:get": "mr-neo",
            "world.PublishersView:get": "helmgast.se",
            "shop.OrdersView:get": db_basic_data["o1"].pk,
            "shop.ProductsView:get": "eon-808",
            "social.UsersView:get": db_basic_data["u1"].pk,
            "world.WorldsView:get": "neotech",
            "assets.FileAssetsView:get": "test/file.png",
            "admin.ShortcutsView:get": "ghijkl",
        },
    }

    def get_expected_response(ep, input):
        res = {
            "shop.OrdersView:details": 200 if input.get("session.uid", None) else 302,
            "shop.OrdersView:my_orders": 200 if input.get("session.uid", None) else 401,
            "shop.OrdersView:pay": 302,
            "shop.OrdersView:get": 200 if input.get("session.uid", None) else 401,
            "shop.OrdersView:index": 200 if input.get("session.uid", None) else 401,
            "key": 302,
            "world.shorturl": 302,
            "world.WorldsView:get": 302,
            "world.ArticlesView:random": 302,
            "admin.ShortcutsView:index": 403,
            "admin.ShortcutsView:get": 403,
            "auth.callback": 400,
            "assets.FileAssetsView:get": 403 if input.get("session.uid", None) else 401,
            "auth.logout": 302,
            "auth.sso": 302,
            "auth.login": 308,
            "auth.join": 308,
            "social.social_home": 308,
            "social.UsersView:get": 200 if input.get("session.uid", None) else 401,
            "social.UsersView:index": 200 if input.get("session.uid", None) else 401,
            "social.me": 302 if input.get("session.uid", None) else 401,
            "assets.index": 302,
            "shop.shop_home": 302,
            "_default": 200,
        }
        if input.get("accept", "") == "application/json" and ep in {
            # "world.homepage",  # doesn't respond in json but can take it as accept
            "world.ArticlesView:publisher_home",
        }:
            return 406  # Not accepted
        if ep in res:
            return res[ep]
        return res["_default"]

    frt = FlaskRouteTester(app_client, all_args, {})
    frt.test_routes(get_expected_response, lambda r: "debug" not in r.endpoint and "logout" not in r.endpoint)
