import pytest
import json

from tools.batch import bulk_update
from lore.model.topic import LORE_BASE, Topic, TopicFactory


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
