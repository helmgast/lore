import pytest
from werkzeug.datastructures import MultiDict
from lore.api.resource import ImprovedBaseForm, MapFormField
from wtforms.fields import StringField
from flask_wtf import FlaskForm


class TestForm(FlaskForm):
    # title = StringField("title")
    map_field = MapFormField(StringField())


class TestObj:
    map_field = {"en": "hello", "es": "hola"}


def test_mapformfield(app_client):

    obj = TestObj()
    formdata = MultiDict()
    formdata["map_field-en"] = "hi"
    formdata["map_field-sv"] = "hej"

    with app_client.application.test_request_context():
        my_form = TestForm(formdata, obj=obj)

    # As we have formdata, that should override what's in the obj data
    d = my_form.map_field.data
    assert d["en"] == "hi"
    assert d["sv"] == "hej"
    assert len(d) == 2


def test_mapformfield_no_formdata(app_client):

    obj = TestObj()
    formdata = MultiDict()


    with app_client.application.test_request_context():
        my_form = TestForm(formdata, obj=obj)

    # As we have formdata, that should override what's in the obj data
    d = my_form.map_field.data
    assert d["en"] == "hello"
    assert d["es"] == "hola"
    assert len(d) == 2


def test_mapformfield_populate(app_client):

    obj = TestObj()
    formdata = MultiDict()
    formdata["map_field-en"] = "hi"
    formdata["map_field-sv"] = "hej"

    with app_client.application.test_request_context():
        my_form = TestForm(formdata, obj=obj)

    # As we have formdata, that should override what's in the obj data
    d = my_form.map_field.data
    assert d["en"] == "hi"
    assert d["sv"] == "hej"
    assert len(d) == 2
    my_form.populate_obj(obj)
    assert obj.map_field["en"] == "hi"
    assert obj.map_field["sv"] == "hej"
    assert len(obj.map_field) == 2
