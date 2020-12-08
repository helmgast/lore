#!/usr/bin/env python

from lore.model.topic import Topic, TopicFactory
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import current_app
import re
from lore.model.shop import job_import_order, job_import_product
from lore.model.world import import_article
from lore.model.user import import_user
from lore.model.import_topic import job_import_sheettopic
from lore.model.misc import to_camelcase
from tools.batch import Batch, Column, bulk_update

# Performance:
# Use a raw query or re-use a Q object
# Return scalar('id').as_pymongo(), will just be an ObjectId


job_funcs = {
    "product": job_import_product,
    "order": job_import_order,
    "article": import_article,
    "user": import_user,
    "topic": job_import_sheettopic,
}

model_field_mapping = {
    "product": {"productNumber": "product_number"},
    "order": {"key": "external_key", "orderLines": "order_lines"},
    "article": {},
    "user": {},
    "topic": {},
}


def import_data(url_or_id, model, sheet, limit, commit, log_level, if_newer=True, **kwargs):
    assert type(url_or_id) == str

    if not limit or limit < 1:
        limit = 1000000  # Just a high number

    scope = ["https://spreadsheets.google.com/feeds"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(current_app.config["GOOGLE_SERVICE_ACCOUNT_PATH"], scope)
    client = gspread.authorize(creds)

    if re.match(r"^https://docs.google.com/spreadsheets.+", url_or_id):
        sh = client.open_by_url(url_or_id)
    else:
        sh = client.open_by_key(url_or_id)

    try:
        if sheet and sheet.isdigit():
            worksheet = sh.get_worksheet(sheet)
        elif sheet:
            worksheet = sh.worksheet(sheet)
        else:
            # Try to find sheet by the gid= parameter in the URL
            gid_match = re.search(r"gid=(\d+)", url_or_id)
            matching_sheets = [x for x in sh.worksheets() if str(x.id) == gid_match.group(1)]
            worksheet = matching_sheets[0]
    except Exception as e:
        raise ValueError("No valid sheet was found, has the sheet been shared correctly?") from e

    data = worksheet.get_all_records()
    if not data:
        raise ValueError("No data was found in the worksheet")

    def stop_at_empty_generator(empty_rows_to_stop=2):
        empty = 0
        for d in data:
            if not "".join(map(str, d.values())).strip():
                empty += 1
                if empty >= empty_rows_to_stop:
                    break
            else:
                empty = 0
                yield d

    if model == "topic":
        data_gen = stop_at_empty_generator()  # Leave case as is
        default_bases = kwargs.pop("default_bases")
        default_scopes = kwargs.pop("default_scopes")
        default_associations = kwargs.pop("default_associations")
        kwargs["topic_factory"] = TopicFactory(default_bases, default_scopes, default_associations)
    else:
        data_gen = (
            {to_camelcase(k): v for k, v in dct.items()} for dct in stop_at_empty_generator()
        )  # Normalize keys to camelCase

    if limit:
        data_gen = list(data_gen)[:limit]
    columns = []

    # Note that columns with same title in worksheet will be overwritten by the rightmost
    headings = data[0].keys()
    for head in headings:
        key = to_camelcase(head) if model != "topic" else head
        columns.append(Column(head, key, model_field_mapping[model].get(key, key)))
    if len(columns) > 6:
        columns = columns[:6]  # Cap length to avoid trying to print too much
    batch = Batch(
        f'Importing from "{sh.title} / {worksheet.title}" ({sh.id} / {worksheet.id})',
        dry_run=not commit,
        log_level=log_level,
        table_columns=columns,
        **kwargs,
    )
    # if repeat_on_empty:
    #     empties = {k: v for k, v in row.items() if v == ""}
    #     if len(empties):
    #         if not last_row:  # Empties in first row that should be used as template
    #             raise ValueError(f"Cannot repeat on empty when first data row is empty at: {empties.keys()}")
    #         row.update({k: last_row[k] for k in empties.keys()})
    #     else:
    #         last_row = row
    batch.process(data_gen, job_funcs[model], if_newer=if_newer)
    if commit and model == "topic":
        bulk_update(Topic, kwargs["topic_factory"].topic_dict.values())

    print(batch.summary_str())
