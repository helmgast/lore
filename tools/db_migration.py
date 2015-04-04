def db_migrate(db, version=''):
	
	# This moves the field shipping_mobile to the right location
	for doc in db.order.find({'shipping_mobile':{'$exists':True}}):
		update = {'$set': {'shipping_address.mobile':doc['shipping_mobile']}, '$unset':{'shipping_mobile':''}}
		results = db.order.update({'_id':doc['_id']}, update)
