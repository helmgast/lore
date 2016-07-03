import os
import re
import gridfs
import tempfile
import pymongo
from bson import DBRef
from flask import g
from pymongo.errors import InvalidName

from fablr.model.asset import FileAsset, ImageAsset
from fablr.model.misc import slugify
from fablr.model.shop import Product
from fablr.model.user import User
from fablr.model.world import Publisher, Article, World


def migrate_1to2():
    """
    Needs to be idempotent, e.g. create same result every time run, even if database already has this version.
    :return:

    """
    succeeded = []
    failed = []

    default_publisher = Publisher.objects(slug='helmgast').first()
    assert default_publisher
    print "Using %s as default publisher" % default_publisher

    hg = World.objects(slug='helmgast').first()
    if hg:
        for a in Article.objects(world=hg):
            a.world = None
            a.publisher = default_publisher
            a.save()
        hg.delete()

    for a in Article.objects():
        print "Replacing image references in article %s" % a
        for match in re.finditer(r'/asset/image/(.+)\)', a.content):
            name, ext = os.path.splitext(match.group(1).lower())
            slug = slugify(name.strip('.')) + '.' + ext.strip('.')
            a.content = a.content[:match.start(1)] + slug + a.content[match.end(1):]
        # Also clean up content
        a.content = re.sub(r' *&nbsp; *', ' ', a.content)
        a.content = re.sub(r'&amp;', u'&', a.content)
        a.content = a.content.strip()
        a.save()

    for w in World.objects():
        w.feature_image = None  # Don't bother migrating, there are few of them and probably wrong anyway
        if not w.publisher:
            w.publisher = default_publisher
        w.save()

    # Ensure we save all FileAsset objects again
    for fa in FileAsset.objects():
        print "Updating %s" % fa
        try:
            file_obj = fa.file_data.get()
            fa.set_file(file_obj, file_obj.filename, update_file=False)
            fa.title = None  # Don't use title again
            fa.save()
            succeeded.append(fa)
        except Exception as e:
          failed.append((e.message, fa))

    for p in Product.objects():
        if not p.publisher or isinstance(p.publisher, DBRef):
            p.publisher = default_publisher

        img = p.feature_image
        # If images have been deleted already, they may show up as DBRef, not as an asset
        if not img:
            slug = None
        elif isinstance(img, DBRef):
            slug = img.id
        elif isinstance(img, ImageAsset):
            slug = img.slug
        print "Migrating image of product %s from ImageAsset (feature_image) to FileAsset (images[])" % p
        try:
            if slug:
                if not p.images:

                        name, ext = os.path.splitext(slug.lower())
                        slug = slugify(name) + '.' + ext
                        fa = FileAsset.objects(slug=slug).first()
                        if fa:
                            p.images = [fa]
                        p.feature_image = None

                else:
                    failed.append(("Will not move image from product %s as it already have images (FileAsset) list" % p, p))
                    continue
            p.save()
            succeeded.append(p)
        except Exception as e:
            failed.append((e.message, p))
            continue

    images = ImageAsset.objects()
    for ia in images:
        fs = ia.image.get()
        fname = fs.filename or ia.id
        ctype = fs.content_type or ia.mime_type
        print "Found %s with format %s and size %s" % (fname, ctype, fs.length)
        try:
            slug = FileAsset.make_slug(fname, ctype)
            # Find existing and replace info as needed
            fileasset = FileAsset.objects(slug=slug).first()
            if not fileasset:
                fileasset = FileAsset()

            fileasset.set_file(fs, filename=fname)
            fileasset.access_type = 'public'  # All ImageAssets are public by default
            fileasset.save()  # Save first to check we can use slug
            ia.delete()
            succeeded.append(fileasset)
        except Exception as e:
            failed.append((e.message, fs.filename))



    # Remove images
    # Remove title from fileasset
    return succeeded, failed

latest_version = 2
migrate_functions = [
    migrate_1to2,
]

def db_migrate(db, to_version=latest_version):
    version = get_version(db)
    admin = User.objects(admin=True).order_by('join_date').first()
    g.user = admin
    print "Current version is %s, making operations as admin user %s" % (version, admin)
    if to_version > latest_version:
        raise ValueError("Cannot migrate to a higher version than latest available (%i)" % latest_version)
    if version is to_version:
        print "Already at version %i" % to_version
        return
    elif version > to_version:
        raise ValueError("Cannot downgrade from version %i to %i" % (version, to_version))
    elif (to_version-1) > len(migrate_functions):
        raise ValueError("No migrate function from version %i to %i" % (version, to_version))
    else:
        for i in range(version-1, to_version-1):
            print "Upgrading from %i to %i" % (i, i+1)
            succeeded, failed = migrate_functions[i]()
            print "  Succeeded with %i" % len(succeeded)
            if failed:
                print "  Failed with %i: %s" % (len(failed), failed)

def get_version(db):
    if 'config' not in db.collection_names():
        db.create_collection('config')
    config = db.config.find_one()
    if not config:
        db.config.insert_one({'version':1})
        return 1
    else:
        return config['version']


    # # This moves the field shipping_mobile to the right location
    # changed = 0
    # for doc in db.order.find({'shipping_mobile': {'$exists': True}}):
    #     update = {'$unset': {'shipping_mobile': ''}}
    #     # Remove old 07XXXXXXXX placeholders
    #     if not doc['shipping_mobile'] == '07XXXXXXXX':
    #         update['$set'] = {'shipping_address.mobile': doc['shipping_mobile']}
    #     results = db.order.update({'_id': doc['_id']}, update)
    #
    # for doc in db.order.find({'shipping_address.mobile': '07XXXXXXXX'}):
    #     update = {'$unset': {'shipping_address.mobile': ''}}
    #     results = db.order.update({'_id': doc['_id']}, update)
    #
    # # Shorten asset links to only slug/filename
    # for doc in db.article.find({'content': {'$regex': ']\(\/asset\/'}}):
    #     update = {'$set': {'content': re.sub(r']\(\/asset\/(\w+\/)*', '](/asset/image/', doc['content'])}}
    #     results = db.article.update({'_id': doc['_id']}, update)
    #
    # fs = gridfs.GridFS(db, 'images')
    # for grid_out in fs.find():
    #     fs.delete(grid_out._id)
    #
    # raw_input("Continue")
    #
    # from fablr.model.asset import ImageAsset
    # for img in ImageAsset.objects().order_by('created_date'):
    #     tmp = open(img.id, "r")
    #     img.image.replace(tmp, content_type=img.mime_type, filename=img.id)
    #     img.save()
    #
    # # fs = gridfs.GridFS(db, 'images')
    # # for doc in db.image_asset.find().sort('created_date', pymongo.ASCENDING):
    # # 	image = fs.get(doc['image'])
    # # 	tmp = tempfile.TemporaryFile()
    # # 	tmp.write(image.read())
    # # 	fs.delete(doc['image'])
    # # 	newid = fs.put(tmp, filename=doc['title'], content_type=doc['mime_type'])
    # # 	db.image_asset.update({'_id':doc['_id']}, {'$set':{'image':newid}})
    # # 	tmp.close()
    # # results = db.images.files.update({'_id':image['_id']},{'$set':update})
