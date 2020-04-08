#!/usr/bin/env python

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from bson.objectid import ObjectId
from urllib.parse import urlparse
from lore.model.shop import Order, OrderStatus, OrderLine, Product
from lore.model.world import Publisher, Article, Shortcut, World, PublishStatus
from lore.model.user import User
from mongoengine import NotUniqueError, Q
from flask import current_app
import re
import datetime


# Input parameters
# Spreadsheet URL
# Data sheet
# Template sheet
# Transform function

# Performance:
# Use a raw query or re-use a Q object
# Return scalar('id').as_pymongo(), will just be an ObjectId

class color:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

OK = f"{color.OKGREEN}✓{color.ENDC}"
FAIL = f"{color.FAIL}✗{color.ENDC}"


def print_row(num, row, warnings=[], error=None):
    """Prints a simple table row. If warnings/error they will get an indented extra row"""
    out = f"{OK}" if not error else f"{FAIL}"
    out += f" {str(num).zfill(4)} "
    for item in row:
        out += str(item)[0:25].ljust(26," ")
    if error:
        out += f"\n    {color.FAIL}{error}{color.ENDC}" 
    for item in warnings:
        out += f"\n    {item}"
    print(out)  


def import_data(url_or_id, sheet, model, repeat_on_empty, commit, maxrows):
    assert(type(url_or_id) == str)

    models = {
        "Order":import_order,
        "Article":import_article
    }

    scope = ['https://spreadsheets.google.com/feeds']
    creds = ServiceAccountCredentials.from_json_keyfile_name(current_app.config['GOOGLE_SERVICE_ACCOUNT_PATH'], scope)
    client = gspread.authorize(creds)
   
    if re.match(r"^https://docs.google.com/spreadsheets.+", url_or_id):
        sh = client.open_by_url(url_or_id)
    else:
        sh = client.open_by_key(url_or_id)
    
    try:
        if sheet and sheet.isdigit():
            data = sh.get_worksheet(sheet)
        elif sheet:
            data = sh.worksheet(sheet)
        else:
            # Try to find sheet by the gid= parameter in the URL
            gid_match = re.search(r"gid=(\d+)", url_or_id)
            matching_sheets = [x for x in sh.worksheets() if str(x.id) == gid_match.group(1)]
            data = matching_sheets[0]
    except Exception as e:
        raise ValueError("No valid sheet was found") from e

    print(f"Importing from \"{sh.title} / {data.title}\" ({sh.id} / {data.id})")

    imported, skipped, last_row = 0, 0, None
    import_model = models[model]
    all_records = data.get_all_records();
    print('\n')
    print("       "+''.join([x[0:25].ljust(26, " ") for x in all_records[0].keys()]))
    print("       "+''.join(["".ljust(25, "-")+" " for x in all_records[0].keys()]))
    for row in all_records:
        if repeat_on_empty:
            empties = {k:v for k, v in row.items() if v == ""}
            if len(empties):
                if not last_row: # Empties in first row that should be used as template
                    raise ValueError(
                    f"Cannot repeat on empty when first data row is empty at: {empties.keys()}")
                row.update({k: last_row[k] for k in empties.keys()})
            else:
                last_row = row
        try:
            savedrow, warnings = import_model(row, commit=commit)
            print_row(imported+skipped, savedrow.values(), warnings=warnings)
            imported += 1
        except Exception as err:
            print_row(imported+skipped, row.values(), error=err)
            skipped += 1
        if imported+skipped >= maxrows:  # Finish after max records
            break
    print("------------------")
    print(f"Imported {imported} and skipped {skipped}")


def user_from_email(email, create=False, commit=False):
    user = User.query_user_by_email(email).scalar('id').as_pymongo().first()
    if create and not user:
        user = User(email=email)
        if commit:
            user.save()
    return user


def import_article(row, commit=False):
    """The model method for importing to Article from text-based data in row"""
    article = Article()
    warnings = []
    title = get(row, "Title", "")
    content = get(row, "Content", "")
    shortcode = get(row, "Shortcode", "").lower()
    created = get(row, "Created", "")
    status = get(row, "Status", "")
    publisher = get(row, "Publisher", "")
    world = get(row, "World", "")
    creator_email = get(row, "Creator", "").lower()
    if not title:
        raise ValueError("Missing compulsory column Title")
    if shortcode:
        count = Shortcut.objects(slug=shortcode).count()
        if count > 0:
            raise ValueError(f"The shortcode {shortcode} is already taken")
    article.created_date = datetime.datetime.strptime(created, '%Y-%m-%d')
    article.creator = user_from_email(creator_email, create=True, commit=commit)
    if status:
        if status not in PublishStatus:
            raise ValueError(f"Publish Status {status} is invalid")    
        else:
            article.status = status  
    if publisher:
        article.publisher = Publisher.objects(slug=publisher).scalar('id').as_pymongo().get()['_id']
    if world:
        article.world = World.objects(slug=world).scalar('id').as_pymongo().get()['_id']
    article.title = title
    article.content = content
    if commit:        
        article.save()
        if shortcode:
            sh = Shortcut(slug=shortcode, article=article.id)
            sh.save()
            article.shortcut = sh
            article.save()

    savedrow = dict(row)
    savedrow['Email'] = article.creator
    savedrow['Publisher'] = article.publisher
    savedrow['World'] = article.world
    savedrow['Created'] = article.created_date
    return savedrow, warnings


def import_order(row, commit=False):
    """The model method for importing to Order from text-based data in row"""
    order = Order()
    warnings = []
    # An order requires that we have order lines, a user/email, and/or an external key
    email = get(row, "Email", "").lower()
    key = get(row, "Key", None)
    orderlines = get(row, "Order Lines", None)
    if not orderlines:
        raise ValueError("Missing order lines")

    def prod_numbers_to_orderlines(prodnumbers):
        """Transforms a string of NNN-111,YYY-123 into a list of OrderLines"""
        prodnumbers = prodnumbers.split(",")
        order_lines = []
        for num in prodnumbers:
            prod = Product.objects(product_number=num).scalar('id').as_pymongo().get()
            order_lines.append(OrderLine(product=prod['_id'], price=0))
        return order_lines
        
    order.order_lines = prod_numbers_to_orderlines(orderlines)

    if not email and not key:
        raise ValueError("No key or email in Order row")
    # Unconfirmed user means "ordered", a step before "paid"
    order.status = OrderStatus.ordered
    if email:
        # This looks for users with primary email, with secondary emails in identities and in auth_keys
        # (only used by old users that haven't upgraded yet)
        user = user_from_email(email, create=True, commit=commit)
        if user:
            order.user = user
        order.status = OrderStatus.paid  # Confirm the order from start as we have a user
        order.email = email
    else:
        order.status = OrderStatus.ordered
    if key:
        # Split in case it starts with a URL
        order.external_key = key.split('/')[-1]

    publisher = get(row, "Publisher", None)
    if publisher:
        order.publisher = Publisher.objects(slug=publisher).scalar('id').as_pymongo().get()['_id']
    title = get(row, "Title", None)
    if title:
        order.title = title
    if commit:
        order.save()
    savedrow = dict(row)
    savedrow['Email'] = order.user
    savedrow['Key'] = order.external_key
    savedrow['Publisher'] = order.publisher
    return savedrow, warnings


DEFAULT = object()


def get(row, key, default=DEFAULT):
    if key in row:
        return row[key]
    elif key.lower() in row:
        return row[key.lower()]
    elif key.upper() in row:
        return row[key.upper()]
    elif default != DEFAULT:
        return default
    else:
        raise KeyError(
            f"Did not find keys {key}, {key.lower()}, {key.upper()}")
