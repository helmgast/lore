from lore.model.topics import Topic, Name, Occurrence, Association
from lore.app import create_app
app = create_app()


def populate_data():
    app.logger.info("Importing topic data")
    # print(app.config['MONGODB_HOST'])
    from mongoengine.connection import get_db
    from lore import extensions
    extensions.db.init_app(app)
    get_db()

    link_type = Topic(id="lore.pub/meta/link", names=[Name(name="Link")])
    link_type.save()

    association_type = Topic(id="lore.pub/meta/is", names=[Name(name="Is")])
    association_type.save()

    instance_role = Topic(id="lore.pub/meta/instance", names=[Name(name="Instance of")])
    instance_role.save()

    category_role = Topic(id="lore.pub/meta/category", names=[Name(name="Category to")])
    category_role.save()

    world = Topic(
        id="lore.pub/meta/world",
        names=[Name(name="World")],
        occurrences=[Occurrence(uri="https://lore.pub/meta/world", occurrence_type=link_type)])
    world.save()

    eon = Topic(
        id="helmgast.se/eon",
        names=[Name(name="Eon")],
        occurrences=[Occurrence(uri="https://helmgast.se/eon", occurrence_type=link_type)])
    eon.save()

    eon.associations = [Association(
        this_topic=eon,
        this_role=instance_role,
        association_type=association_type,
        other_role=category_role,
        other_topic=world
        )]
    eon.save()

    domain = Topic(
        id="lore.pub/meta/domain",
        names=[Name(name="Domain")],
        occurrences=[Occurrence(uri="https://lore.pub/meta/domain", occurrence_type=link_type)])
    domain.save()

    drunok = Topic(
        id='helmgast.se/eon/drunok',
        names=[Name(name="Drunok")],
        occurrences=[Occurrence(uri="https://helmgast.se/eon/drunok", occurrence_type=link_type)])
    drunok.save()


populate_data()