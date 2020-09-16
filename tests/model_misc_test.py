import pytest
from flask import request, url_for, g


def test_get():
    from lore.model.misc import get

    assert get({"a": 1}, "a") == 1

    assert get({"a": 1}, "b", "c") == "c"

    # Need one with (context manager) each
    with pytest.raises(KeyError):
        get(None, None)
    with pytest.raises(KeyError):
        get({}, "a")
    with pytest.raises(KeyError):
        get({"a": 1}, "b")
    with pytest.raises(KeyError):
        get({"a": {"b": 2}}, "a.b.c")

    assert get({"a": {"b": 2}}, "a.b") == 2

    assert get({"a": {"b": 2}}, "a") == {"b": 2}

    assert get({"a": {"b": 2}}, "a.b.c", "d") == "d"

    assert get({}, "a", default="b") == "b"


# current_url(_external=true)
# current_url(page=pagination.next_num, _external=true, _scheme='')
# current_url(lang=locale.language)
# current_url(pub_host=lore.test)  # Test we can do url with global defaults
# current_url(view='card')
# current_url(order_by=none)
# current_url(combine, full_url=full_url, **dict.fromkeys(argdict.keys(), none))
# current_url(page=page)
# current_url()  # Should just return current URL with all args as is
# current_url(intent=None, out=None, _external=true, _scheme='')  # remove args, and make external, as we are in a modal and may have a different URL
# current_url should follow (almost) same signature as url_for
# current_url()  # Tricky case, if we give query_arg=[1,2] will it be theurl.com?query_arg=1&query_arg=2 ?
# url_for(endpoint, **values) where values can have view_args, _external, _scheme, _anchor, _method.
# Any other argument will become an url parameter after ?, unless it's None, where the arg should be ignored altogether
def test_current_url(app_client):
    from lore.model.misc import current_url

    app_client.application.config["PRODUCTION"] = True
    with app_client.application.test_request_context("https://helmgast.se/en/eon/articles/?type=default"):
        # Manually set as test_request doesn't launch the url preprocess?
        g.pub_host = "helmgast.se"
        g.lang = "en"
        assert request.endpoint == "world.ArticlesView:index"
        assert request.view_args == {"lang": "en", "world_": "eon", "pub_host": "helmgast.se"}

        assert current_url() == "/en/eon/articles/?type=default"
        assert current_url(_external=True) == "http://helmgast.se/en/eon/articles/?type=default"  # defaults http
        assert current_url(type="different") == "/en/eon/articles/?type=different"
        assert current_url(type=None) == "/en/eon/articles/"
        assert current_url(lang="sv") == "/eon/articles/?type=default"  # sv defaults to no lang code
        assert current_url(pub_host="lore.pub") == "http://lore.pub/en/eon/articles/?type=default"  # defaults http
        assert current_url(view=["a", "b"], type=None) == "/en/eon/articles/?view=a&view=b"

    with app_client.application.test_request_context("https://helmgast.se/en/eon/articles/?view=a&view=b"):
        g.pub_host = "helmgast.se"
        g.lang = "en"
        assert current_url(view="c") == "/en/eon/articles/?view=c"
        assert current_url(view="b", toggle=True) == "/en/eon/articles/?view=a"
        assert current_url(view="b", merge=True, toggle=True) == "/en/eon/articles/?view=a"
        assert current_url(view="c", merge=True, toggle=True) == "/en/eon/articles/?view=a&view=b&view=c"

        # assert request.view_args ==


# def test_mapdict(app_client):
#     from lore.model.misc import get, Test

#     from lore import extensions
#     from mongoengine.connection import get_db

#     extensions.db.init_app(app_client.application)
#     db = get_db()

#     t = Test()
#     # t.mapfield = {}
#     t.mapfield["a"] = "b"
#     assert "a" in t.mapfield
#     t.dictfield["d"] = "e"
#     t.dictfield["f"] = 7
#     assert "f" in t.dictfield
#     t.save()
