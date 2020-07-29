import pytest

@pytest.fixture()
def basic_app_data(app_client):
    from lore.model.world import Publisher, World, Article

    db = object()
    with app_client.application.test_request_context():
        db.hg = Publisher(slug="helmgast.se", title="Helmgast AB").save()
        db.op = Publisher(slug="otherpub.com", title="OtherPub").save()
        db.neo = World(slug="neotech", title="Neotech", publisher=db.hg).save()
        db.eon = World(slug="eon", title="Eon", publisher=db.hg).save()
        db.a1 = Article(slug="neo-article", title="Neotech Article", world=db.neo, publisher=db.hg).save()
        db.a2 = Article(slug="eon-article", title="Eon Article", world=db.eon, publisher=db.hg).save()

    return db

def test_publishers_view(app_client, basic_app_data):
    pass
