import pytest
from lore.model.user import User, Event
from datetime import datetime


@pytest.fixture()
def db_loaded_user_data(app_client):
    with app_client.application.test_request_context():
        u1 = User(
            username="test1",
            email="test1@test.com",
            realname="Test1 Testsson",
            location="New York",
            join_date=datetime(2020, 1, 1),
            auth_keys=["test1@old.com|google-oauth2|12123123123123123"],
        ).save()
        u2 = User(
            username="test2",
            email="test2@test.com",
            realname="Test2 Testsson",
            description="Yada",
            location="Tokyo",
            join_date=None,
            identities=[
                {
                    "provider": "google-oauth2",
                    "user_id": "113968856999659339381",
                    "connection": "google-oauth2",
                    "isSocial": True,
                },
                {
                    "profileData": {"email": "test2@helmgast.se", "email_verified": True},
                    "user_id": "58ba793c0bdcab0a0ec46cf7",
                    "provider": "email",
                    "connection": "email",
                    "isSocial": False,
                },
            ],
        ).save()
        u2.log("test", None)  # Log dummy event so we can change it in tests
    return {"u1": u1, "u2": u2}


def test_user_query(mongomock, app_client, db_loaded_user_data):

    users = User.query_user_by_email("test1@test.com", return_deleted=False)
    assert len(users) == 1
    users = User.query_user_by_email("test1@old.com", return_deleted=False)
    assert len(users) == 1
    users = User.query_user_by_email("test2@test.com", return_deleted=False)
    assert len(users) == 1
    users = User.query_user_by_email("test2@helmgast.se", return_deleted=False)
    assert len(users) == 1
    db_loaded_user_data["u2"].status = "deleted"
    db_loaded_user_data["u2"].save()
    users = User.query_user_by_email("test2@helmgast.se", return_deleted=False)
    assert len(users) == 0
    users = User.query_user_by_email("test2@helmgast.se", return_deleted=True)
    assert len(users) == 1


def test_merge_users(mongomock, app_client, db_loaded_user_data):

    db_loaded_user_data["u1"].merge_in_user(db_loaded_user_data["u2"])
    assert db_loaded_user_data["u1"].description == "Yada"  # Taken from u2
    assert db_loaded_user_data["u1"].realname == "Test1 Testsson"
    assert db_loaded_user_data["u2"].status == "deleted"
    assert db_loaded_user_data["u2"].identities is None
    events = Event.objects(action="test")
    assert len(events) == 1
    # log item for U2 was changed to U1
    assert events[0].user == db_loaded_user_data["u1"]
