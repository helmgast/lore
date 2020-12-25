from flask import current_app
from jsonrpcclient.clients.http_client import HTTPClient
from jsonrpcclient.requests import Request
from lore.model.shop import import_product, job_import_product, job_import_order
from tools.batch import Batch, LogLevel, Column
from lore.model.misc import get
import json

if "TEXTALK_URL" in current_app.config:
    rpc_client = HTTPClient(current_app.config.get("TEXTALK_URL"))


def rpc_get(method, *args):
    r = Request(method, *args)
    response = rpc_client.send(r)
    return response.data.result


def rpc_list(method, *args, **kwargs):
    # "params": [["uid", "name"], {"filters": {"/draft": false}, "limit": 10, "offset": 0}]
    # te-theme', 'trouble-theme', 'vintage-form-theme'] ()
    # "method": "Article.list", "params": [["uid", "name"], {"filters": {"/draft": false}}, {"limit": 10, "offset": 0}], "id": 1}
    # Max page size

    total_limit = kwargs.pop("total_limit", 0)
    page_limit = min(total_limit if total_limit > 0 else 400, 400)
    if kwargs:
        kwargs["limit"] = page_limit
        kwargs["offset"] = 0
    result, returned = [], page_limit
    while returned == page_limit and kwargs.get("limit") > 0:
        # If not equal, we got less than we asked for and has reached the end of the list
        r = Request(method, *args, **kwargs)
        print(r)
        response = rpc_client.send(r)
        result.extend(response.data.result)
        returned = len(response.data.result)
        if kwargs:
            kwargs["offset"] = kwargs["offset"] + page_limit
            if total_limit > 0 and kwargs["offset"] + page_limit > total_limit:
                # We need less then another page to fulfill total, so we will set next query to be small enough
                kwargs["limit"] = total_limit - kwargs["offset"]
    return result


product_default_fields_to_return = [
    "uid",
    "name",
    "created",
    "changed",
    "articleNumber",
    "introductionText",
    "price",
    "url",
    "stock",
    "images",
    "hidden",
    "weight",
    "vatRate",
    "freeFreight",
]


def import_articles(fields_to_return=None, commit=False, log_level=LogLevel.INFO, limit=0, filter="", **kwargs):
    # args to add: filter, customizable fields_to_return, template data, replace or not
    if not fields_to_return:
        fields_to_return = product_default_fields_to_return
    if "publisher" not in kwargs:
        raise ValueError("Requires a publisher domain")
    filters = {"/draft": False}
    if filter:
        try:
            filters.update(json.loads(filter))
        except Exception:
            pass
    data = rpc_list("Article.list", fields_to_return, filters=filters, total_limit=limit)
    columns = [
        Column("TITLE                                  ", "name", "title"),
        Column("ART#     ", "articleNumber", "product_number"),
        Column("CREATED                  ", "created", "created"),
        Column("STATUS       ", "hidden", "status"),
        Column("TYPE     ", "", "type"),
    ]
    batch = Batch("Import Textalk products", dry_run=not commit, log_level=log_level, table_columns=columns, **kwargs)
    batch.process(data, job_import_product)
    print(batch.summary_str())


delivery_methods = {}


def add_delivery_method(order_data):
    """Replaces a uid field with name of delivery methods.
    Fetches all delivery methods in one go and caches the result in global variable.

    Arguments:
        order_data {[type]} -- [description]
    """
    global delivery_methods
    key = get(order_data, "delivery.method", None)
    if not key:
        return
    if key not in delivery_methods:
        response = rpc_list("DeliveryMethod.list", ["uid", "name"])
        delivery_methods = {method["uid"]: method["name"] for method in response}
    if key in delivery_methods:
        order_data["delivery"]["method"] = delivery_methods[key]


order_default_fields_to_return = {
    "uid": True,
    "ordered": True,
    "changed": True,
    "currency": True,
    "delivery": True,
    "language": True,
    "paymentStatus": True,
    "customer": {"info": True, "address": True},
    "costs": {"shipment": True},
    "items": ["costs", "articleNumber", "discountInfo", "choices", "download", "articleName"],
}


def import_orders(fields_to_return=None, commit=False, log_level=LogLevel.INFO, limit=0, filter="", **kwargs):
    if not fields_to_return:
        fields_to_return = order_default_fields_to_return
    if "publisher" not in kwargs:
        raise ValueError("Requires a publisher domain")
    filters = {"/discarded": False, "/customer/info/type": {"equals": "individual"}}
    if filter:
        filters.update(json.loads(filter))

    data = rpc_list("Order.list", fields_to_return, filters=filters, total_limit=limit)
    # for d in data:
    #     add_delivery_method(d)

    batch = Batch(
        "Import Textalk orders",
        dry_run=not commit,
        log_level=log_level,
        table_columns=[
            Column("KEY", "uid", "external_key"),
            Column("EMAIL", "email", "email"),
            Column("CREATED", "ordered", "created"),
            Column("PRICE", "", "total_price"),
        ],
        **kwargs
    )
    batch.process(data, job_import_order)
    print(batch.summary_str())


# Import Products from Textalk
# Article.list(
#   ,
#   {
#     "filters": {
#       "search": {
#         "term": "kottar",
#         "relevance": 100
#       }
#     },
#     "limit": 4
#   }
# )
