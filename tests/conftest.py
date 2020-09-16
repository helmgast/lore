from flask.testing import FlaskClient
import pytest


@pytest.fixture
def mongomock(scope="session"):
    from mongoengine import connect, disconnect
    from mongomock import gridfs

    gridfs.enable_gridfs_integration()
    yield connect("mongoenginetest", host="mongomock://localhost")
    disconnect()


@pytest.fixture
def app_client(scope="session") -> FlaskClient:
    # PRESERVE_CONTEXT... needed for avoiding context pop error, see
    # http://stackoverflow.com/questions/26647032/py-test-to-test-flask-register-assertionerror-popped-wrong-request-context
    # WTF_CSRF_CHECK_DEFAULT turn off all CSRF, test that in specific case only
    from lore.app import create_app

    app = create_app(TESTING=True, PRESERVE_CONTEXT_ON_EXCEPTION=False, WTF_CSRF_CHECK_DEFAULT=False)
    with app.test_client(use_cookies=False) as client:
        yield client


@pytest.fixture
def mocked_responses():
    import responses

    with responses.RequestsMock() as rsps:
        yield rsps
