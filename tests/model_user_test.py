import pytest
from lore.model.user import User


def test_user_query(app_client):
    from lore import extensions
    from mongoengine.connection import get_db

    extensions.db.init_app(app_client.application)
    db = get_db()
    users = User.query_user_by_email("martinfrojd@outlook.com", return_deleted=False)

    assert len(users) == 1


def test_merge_users(app_client):
    pass
