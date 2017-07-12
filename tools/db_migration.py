#!/usr/bin/env python

from __future__ import print_function
from builtins import range
from past.builtins import basestring
import os
import re
import traceback

import gridfs
import tempfile
import pymongo
from bson import DBRef
from flask import g
from mongoengine import NotUniqueError, DoesNotExist
from pymongo.errors import InvalidName

from fablr.model.asset import FileAsset, ImageAsset
from fablr.model.misc import slugify
from fablr.model.shop import Product, Order, OrderStatus
from fablr.model.user import User, Event
from fablr.model.world import Publisher, Article, World


# All migration functions needs to be idempotent, e.g. create same result every time run, even if database already has this version.

def set_default_reference(obj, attr, default_value):
    try:
        ref = getattr(obj, attr, None)
    except DoesNotExist as dne:
        ref = None
    if not ref or isinstance(ref, DBRef) or isinstance(ref, basestring):
        setattr(obj, attr, default_value)

def migrate_2to3():
    succeeded = []
    failed = []

    print("Adding previous purchases to event log")
    for o in Order.objects(status=OrderStatus.paid):
        ev2 = Event(user=o.user, action='purchase', resource=o, metric=o.total_price_sek(), created=o.created)
        msg = u"%s" % o
        try:
            ev2.save()
        except NotUniqueError as nue:
            pass
        except Exception as e:
            failed.append((e.message, msg))
            continue
        succeeded.append(msg)

    users = User.objects()
    print("Migrating event logs from users to separate Collection")
    for u in users:
        if getattr(u, 'event_log', None):
            for ev in u.event_log:
                msg = u"%s %s %s" % (u, ev.action, ev.created.strftime('%Y-%m-%d %H:%M:%S'))
                ev2 = Event(user=u, action=ev.action, resource=ev.instance, message=ev.message)
                try:
                    ev2.save()  # Only save if same event doesn't already exist
                    u.event_log = None
                except NotUniqueError as nue:
                    pass
                except Exception as e:
                    failed.append((e.message, msg))
                    continue
                succeeded.append(msg)
        u.save()  # Save to re-calc XP etc

    return succeeded, failed


def migrate_1to2():
    succeeded = []
    failed = []

    default_publisher = Publisher.objects(slug='helmgast.se').first()
    if not default_publisher:
        default_publisher = Publisher(slug='helmgast.se', title='Helmgast')
        default_publisher.save()
    print("Using %s as default publisher" % default_publisher)

    hg = World.objects(slug='helmgast').first()
    if hg:
        hg.delete()

    for w in World.objects():
        w.feature_image = None  # Don't bother migrating, there are few of them and probably wrong anyway
        if not w.publisher or isinstance(w.publisher, DBRef):
            w.publisher = default_publisher
        w.save()

    # Ensure we save all FileAsset objects again
    for fa in FileAsset.objects():
        print("Updating %s" % fa)
        try:
            file_obj = fa.file_data.get()
            fa.set_file(file_obj, file_obj.filename, update_file=False)
            fa.title = None  # Don't use title again
            fa.publisher = default_publisher
            fa.save()
            succeeded.append(fa)
        except Exception as e:
            failed.append((e.message, fa))

    images = ImageAsset.objects()
    for ia in images:
        fs = ia.image.get()
        fname = fs.filename or ia.id
        ctype = fs.content_type or ia.mime_type
        print("Found %s with format %s and size %s" % (fname, ctype, fs.length))
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

    for p in Product.objects().no_dereference():
        p.publisher = default_publisher

        img = p.feature_image
        # If images have been deleted already, they may show up as DBRef, not as an asset

        if not img:
            slug = None
        elif isinstance(img, DBRef):
            slug = img.id
        elif isinstance(img, ImageAsset):
            slug = img.slug
        elif isinstance(img, basestring):
            slug = img
        print("Migrating image of product %s from ImageAsset (feature_image) to FileAsset (images[])" % p)
        try:
            if slug:
                if not p.images:
                    name, ext = os.path.splitext(slug.lower())
                    slug = slugify(name) + ext  # Includes the .
                    fa = FileAsset.objects(slug=slug).first()
                    if fa:
                        p.images = [fa]
                    p.feature_image = None
                    p.save()
                    succeeded.append(p)
                else:
                    failed.append(
                        ("Will not move image from product %s as it already have images (FileAsset) list" % p, p))
                    continue
        except Exception as e:
            failed.append((e.message, p))
            continue

    def asset_repl(match):
        name, ext = os.path.splitext(match.group(5).lower())
        slug = slugify(name.strip('.')) + '.' + ext.strip('.')
        return u"[{alt}](https://fablr.co/asset/{type}/{slug})".format(alt=match.group(1), type=match.group(4), slug=slug)

    for a in Article.objects():
        print("Replacing image references in article %s" % a)
        a.content = re.sub(r'\[([^]]*)\]\((http(s)?://helmgast.se)?/asset/(image|download|link)/([^)]+)\)',
                           asset_repl, a.content)
        a.content = re.sub(r'http://helmgast', 'https://helmgast', a.content)

        # Also clean up content
        a.content = re.sub('\xe2\x80\xa2', '*', a.content)
        a.content = re.sub(r' *&nbsp; *', ' ', a.content)
        a.content = re.sub(r'&amp;', '&', a.content)
        a.content = a.content.strip()
        set_default_reference(a, 'publisher', default_publisher)
        set_default_reference(a, 'world', None)
        a.save()

    # Remove images
    # Remove title from fileasset
    return succeeded, failed


latest_version = 3
migrate_functions = [
    migrate_1to2,
    migrate_2to3
]


def db_migrate(db, to_version=latest_version):
    version = get_version(db)
    admin = User.objects(admin=True).order_by('join_date').first()
    g.user = admin
    print("DB version is %s, latest code is version %s, will migrate using admin user %s" % \
          (version, latest_version, admin))
    if to_version > latest_version:
        raise ValueError("Cannot migrate to a higher version than latest available (%i)" % latest_version)
    if version is to_version:
        print("Already at version %i" % to_version)
        return
    elif version > to_version:
        raise ValueError("Cannot downgrade from version %i to %i" % (version, to_version))
    elif (to_version - 1) > len(migrate_functions):
        raise ValueError("No migrate function from version %i to %i" % (version, to_version))
    else:
        config = db.config.find_one()
        for i in range(version, to_version):
            print("Upgrading from %i to %i" % (i, i + 1))
            try:
                succeeded, failed = migrate_functions[i-1]()  # 0-indexed, but version is 1-indexed
            except Exception as ex:
                print("Fatal error, stopping migration with function %i : %s" % (i, ex))
                traceback.print_exc()
                return False
            print("  Succeeded with %i" % len(succeeded))
            if not failed:
                # Increment version by one
                result = db.config.update_one({'version': i}, {'$inc': {'version': 1}})
                if result.modified_count == 0:
                    print("Fatal error, could not update version # on collection 'config'")
                    return False
                else:
                    print("Updated database version from %i to %i" % (i, i+1))
            else:
                print("  Failed with %i: %s" % (len(failed), failed))
                print("Stopping migration until above failure handled manually")
                return False
    return True


def get_version(db):
    if 'config' not in db.collection_names():
        db.create_collection('config')
    config = db.config.find_one()
    if not config:
        db.config.insert_one({'version': 1})
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
