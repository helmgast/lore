from run import test
import pytest
import json

from tools.batch import Batch, Job, bulk_update
from lore.model.topic import LORE_BASE, Topic, TopicFactory, create_basic_topics
from lore.model.import_topic import job_import_sheettopic, job_import_topic


def dict_except(doc, *not_keys):
    dct = doc.to_mongo().to_dict()
    return {x: dct[x] for x in dct if x not in not_keys}


@pytest.fixture()
def topic_db_import(app_client, mongomock):
    factory = TopicFactory()
    t1 = factory.make_topic("t1", [("English t1", f"{LORE_BASE}en"), ("Svensk t1", f"{LORE_BASE}sv")], kind="t2")
    t2 = factory.make_topic("t2", "Topic", desc="A topic desc", kind="other_t")
    factory.make_association("Alternative naming", "Alias", "Alias for", "Primary", "Aliased by")
    t1.add_association(t2, "alternative_naming", "alias", "primary")
    bulk_update(Topic, factory.topic_dict.values())
    db = {t.pk: t for t in Topic.objects()}
    return db


@pytest.fixture()
def expected_topic_dicts():
    return {
        "t1": {
            "_id": "t1",
            "kind": "t2",
            "names": [
                {"name": "English t1", "scopes": [f"{LORE_BASE}en"]},
                {"name": "Svensk t1", "scopes": [f"{LORE_BASE}sv"]},
            ],
            "occurrences": [],
            "associations": [
                {"r1": "alias", "kind": "alternative_naming", "r2": "primary", "t2": "t2", "scopes": [],}
            ],
        },
        "t2": {
            "_id": "t2",
            "kind": "other_t",
            "names": [{"name": "Topic", "scopes": []}],
            "occurrences": [
                {"content": "A topic desc", "kind": f"{LORE_BASE}description", "scopes": [f"{LORE_BASE}en"]}
            ],
            "associations": [
                {"r1": "primary", "kind": "alternative_naming", "r2": "alias", "t2": "t1", "scopes": [],}
            ],
        },
    }


def test_import_clean(topic_db_import, expected_topic_dicts):
    db = topic_db_import
    expected = expected_topic_dicts

    # Not testing created and updated as they will not be deterministic
    assert dict_except(db["t1"], "created_at", "updated_at") == expected["t1"]

    assert dict_except(db["t2"], "created_at", "updated_at") == expected["t2"]

    # Currently, we are NOT creating empty topics in advance
    # Should have created this topic as well
    # assert db["other_t"].id == "other_t"
    # assert len(db["other_t"].names) == 0  # But without any name

    assert db["alias"].id == "alias"

    assert db["alternative_naming"].id == "alternative_naming"
    assert db["alternative_naming"].kind.id == f"{LORE_BASE}association"
    assert len(db["alternative_naming"].names) == 3

    # Import again to test no change, e.g no duplication
    db = topic_db_import

    assert dict_except(db["t1"], "created_at", "updated_at") == expected["t1"]

    assert dict_except(db["t2"], "created_at", "updated_at") == expected["t2"]

    # Currently, we are NOT creating empty topics in advance
    # Should have created this topic as well
    # assert db["other_t"].id == "other_t"
    # assert len(db["other_t"].names) == 0  # But without any name

    assert db["alias"].id == "alias"

    assert db["alternative_naming"].id == "alternative_naming"
    assert db["alternative_naming"].kind.id == f"{LORE_BASE}association"
    assert len(db["alternative_naming"].names) == 3


def test_import_updates_correctly(topic_db_import, expected_topic_dicts):
    db = topic_db_import
    factory = TopicFactory(topic_dict=db)

    # Types of updates to do
    # 1) Update singular fields like kind and created_at
    # 2) Add items to lists of characteristics (names, occ, ass)
    t2 = factory.make_topic(id="t2", names=("Another name", f"{LORE_BASE}en"), kind="new_instance")
    expected_topic_dicts["t2"]["kind"] = "new_instance"
    expected_topic_dicts["t2"]["names"].append({"name": "Another name", "scopes": [f"{LORE_BASE}en"]})

    assert dict_except(db["t2"], "created_at", "updated_at") == expected_topic_dicts["t2"]

    # 3) Remove items to lists of characteristics (names, occ, ass)
    found = db["t1"].find_names(name="English t1", indices=True)
    db["t1"].names.pop(found[0][0])  # First found item, index is first of tuple
    expected_topic_dicts["t1"]["names"].pop(0)

    assert dict_except(db["t1"], "created_at", "updated_at") == expected_topic_dicts["t1"]

    # 4) Update items in lists of characteristics (names, occ, ass)

    # 5) Update id (shouldn't be done!)

    # 6) An update above, may trigger changes on another topic (if ass), or may trigger the creation of a new topic (e.g. a new scope, instance)
    # TODO should be create new topics just based on a reference? Or should they be created lazily, when there is actually some information to add?

    # TODO test if we call make_topic, add_name without args to None is given. This gave errors that we autoconverted the None to a list or string


def test_import_from_sheets(app_client, mongomock):
    test_data = {
        "Name #": "ONN | Orbital News Network",
        "Type =": "Corporation",
        "Description [en] &": "One of the world's largest news channels. Formally based in orbit and therefore theoretically neutral.",
        "Part of @": "Farring",
        "Referred in": "Överallt",
        "Description [sv] &": "",
        "Reference [sv] &": """
PRD: 011, 015, 019, 021, 025, 029, 033, 043, 049, 063, 067, 077, 081, 087, 109, 121
anon: 019–021, 024, 033, 074–075, 079, 083–084, 088–089, 129, 133, 143
PRD: 60
anon: 021, 088""",
    }
    c = {"topic_factory": TopicFactory(default_bases=["lore.pub/t", "me.pub"], topic_dict=create_basic_topics(False))}
    job_import_sheettopic(job=Job(test_context=c), data=test_data)
    d = c["topic_factory"].topic_dict

    print(dict_except(d["me.pub/onn"], "created_at", "updated_at"))

    assert dict_except(d["me.pub/onn"], "created_at", "updated_at") == {
        "_id": "me.pub/onn",
        "kind": "lore.pub/t/corporation",
        "names": [{"name": "ONN", "scopes": []}, {"name": "Orbital News Network", "scopes": []}],
        "occurrences": [
            {
                "content": "One of the world's largest news channels. Formally based in orbit and therefore theoretically neutral.",
                "kind": "lore.pub/t/description",
                "scopes": ["lore.pub/t/en"],
            },
            {
                "content": "PRD: pp. 11, 15, 19, 21, 25, 29, 33, 43, 49, 63, 67, 77, 81, 87, 109, 121, 60",
                "kind": "lore.pub/t/bibref",
                "scopes": ["lore.pub/t/sv"],
            },
            {
                "content": "anon: pp. 19–21, 24, 33, 74–75, 79, 83–84, 88–89, 129, 133, 143, 21, 88",
                "kind": "lore.pub/t/bibref",
                "scopes": ["lore.pub/t/sv"],
            },
        ],
        "associations": [
            {
                "r1": "lore.pub/t/part",
                "kind": "lore.pub/t/inclusion",
                "r2": "lore.pub/t/whole",
                "t2": "me.pub/farring",
                "scopes": [],
            }
        ],
    }
    assert dict_except(d["me.pub/farring"], "created_at", "updated_at") == {
        "_id": "me.pub/farring",
        "names": [{"name": "Farring", "scopes": []}],
        "occurrences": [],
        "associations": [
            {
                "r1": "lore.pub/t/whole",
                "kind": "lore.pub/t/inclusion",
                "r2": "lore.pub/t/part",
                "t2": "me.pub/onn",
                "scopes": [],
            }
        ],
    }


# To test
# Fields with / , etc in them, but aren't intended to be split.
# Fields with multiple valid separators, e.g. |, but without content or just whitespace between, e.g. '| | A | B | '
# id specified in column with or without full domain
# whitespace in end or beginning of all parts of the parsed "formula" from cells


def test_import_from_md(app_client, mongomock):
    import frontmatter

    test_data = """
---
author: Lycan
created_at: '2012-09-22T23:26:06Z'
id: Ϡ
links:
  category:
  - t2: Symboler
    scopes: sv
  mention:
  - Malkom Trevena
  occurrence:
  - '03E0-500x500.png'
occurrences:
  description:
  - content: asdaasda
    scopes: en
title: Ϡ
---
Some test text here, and a link to [Malkom Trevenas]

![][1]

  [Malkom Trevenas]: Malkom_Trevena
  [1]: 03E0-500x500.png "03E0-500x500.png"
"""
    doc = frontmatter.loads(test_data)

    c = {"topic_factory": TopicFactory(default_bases=["lore.pub/t", "me.pub"], topic_dict=create_basic_topics(False))}
    job_import_topic(job=Job(test_context=c), data=doc)
    d = c["topic_factory"].topic_dict

    # print(dict_except(d["me.pub/ϡ"], "created_at", "updated_at"))

    assert dict_except(d["me.pub/ϡ"], "created_at", "updated_at") == {
        "_id": "me.pub/ϡ",
        "names": [{"name": "Ϡ", "scopes": ["lycan@me.pub"]}],
        "occurrences": [
            {
                "content": 'Some test text here, and a link to [Malkom Trevenas]\n\n![][1]\n\n  [Malkom Trevenas]: https://me.pub/malkom_trevena\n  [1]: 03E0-500x500.png "03E0-500x500.png"',
                "kind": "lore.pub/t/article",
                "scopes": ["lycan@me.pub"],
            },
            {"content": "asdaasda", "kind": "lore.pub/t/description", "scopes": ["lore.pub/t/en", "lycan@me.pub"]},
            {"uri": "03E0-500x500.png", "kind": "lore.pub/t/image", "scopes": ["lycan@me.pub"]},
        ],
        "associations": [
            {
                "r1": "lore.pub/t/sample",
                "kind": "lore.pub/t/categorization",
                "r2": "lore.pub/t/category",
                "t2": "me.pub/symboler",
                "scopes": ["lycan@me.pub"],
            },
            {
                "r1": "lore.pub/t/source",
                "kind": "lore.pub/t/link",
                "r2": "lore.pub/t/target",
                "t2": "me.pub/malkom_trevena",
                "scopes": ["lycan@me.pub"],
            },
        ],
    }
    assert dict_except(d["lycan@me.pub"], "created_at", "updated_at") == {
        "_id": "lycan@me.pub",
        "names": [{"name": "Lycan", "scopes": []}],
        "occurrences": [],
        "associations": [],
    }
    assert dict_except(d["me.pub/malkom_trevena"], "created_at", "updated_at") == {
        "_id": "me.pub/malkom_trevena",
        "names": [{"name": "Malkom Trevena", "scopes": ["lycan@me.pub"]}],
        "occurrences": [],
        "associations": [
            {
                "r1": "lore.pub/t/target",
                "kind": "lore.pub/t/link",
                "r2": "lore.pub/t/source",
                "t2": "me.pub/ϡ",
                "scopes": ["lycan@me.pub"],
            }
        ],
    }
    assert dict_except(d["me.pub/symboler"], "created_at", "updated_at") == {
        "_id": "me.pub/symboler",
        "names": [{"name": "Symboler", "scopes": ["lore.pub/t/sv", "lycan@me.pub"]}],
        "occurrences": [],
        "associations": [
            {
                "r1": "lore.pub/t/category",
                "kind": "lore.pub/t/categorization",
                "r2": "lore.pub/t/sample",
                "t2": "me.pub/ϡ",
                "scopes": ["lycan@me.pub"],
            }
        ],
    }
