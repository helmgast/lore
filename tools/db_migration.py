import re
import gridfs
import tempfile
import pymongo


def db_migrate(db, version=''):
    # This moves the field shipping_mobile to the right location
    changed = 0
    for doc in db.order.find({'shipping_mobile': {'$exists': True}}):
        update = {'$unset': {'shipping_mobile': ''}}
        # Remove old 07XXXXXXXX placeholders
        if not doc['shipping_mobile'] == '07XXXXXXXX':
            update['$set'] = {'shipping_address.mobile': doc['shipping_mobile']}
        results = db.order.update({'_id': doc['_id']}, update)

    for doc in db.order.find({'shipping_address.mobile': '07XXXXXXXX'}):
        update = {'$unset': {'shipping_address.mobile': ''}}
        results = db.order.update({'_id': doc['_id']}, update)

    # Shorten asset links to only slug/filename
    for doc in db.article.find({'content': {'$regex': ']\(\/asset\/'}}):
        update = {'$set': {'content': re.sub(r']\(\/asset\/(\w+\/)*', '](/asset/image/', doc['content'])}}
        results = db.article.update({'_id': doc['_id']}, update)

    fs = gridfs.GridFS(db, 'images')
    for grid_out in fs.find():
        fs.delete(grid_out._id)

    raw_input("Continue")

    from fablr.model.asset import ImageAsset
    for img in ImageAsset.objects().order_by('created_date'):
        tmp = open(img.id, "r")
        img.image.replace(tmp, content_type=img.mime_type, filename=img.id)
        img.save()

    # fs = gridfs.GridFS(db, 'images')
    # for doc in db.image_asset.find().sort('created_date', pymongo.ASCENDING):
    # 	image = fs.get(doc['image'])
    # 	tmp = tempfile.TemporaryFile()
    # 	tmp.write(image.read())
    # 	fs.delete(doc['image'])
    # 	newid = fs.put(tmp, filename=doc['title'], content_type=doc['mime_type'])
    # 	db.image_asset.update({'_id':doc['_id']}, {'$set':{'image':newid}})
    # 	tmp.close()
    # results = db.images.files.update({'_id':image['_id']},{'$set':update})
