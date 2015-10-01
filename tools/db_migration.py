def db_migrate(db, version=''):
	
	# This moves the field shipping_mobile to the right location
	changed = 0
	for doc in db.order.find({'shipping_mobile':{'$exists':True}}):
		results = db.order.update(
			{'_id':doc['_id']},
			{'$set': {'shipping_address.mobile':doc['shipping_mobile']}})
		print results
		changed += results.modified_count
	print "Migrated shipping mobile on %i orders" % changed

	# Changed world.publisher from a string to a Reference
	# First remove all old publisher references
	result = db.world.update({'publisher':{'$type':2}}, {'$unset':{'publisher':''}}, multi=True) # remove worlds with string fields as publisher
	print "Removed old publisher field on %i worlds" % result['n']

	doc = db.publisher.find_one({'slug':'helmgast'})
	if not doc:
		hg_publisher = db.publisher.insert({'slug':'helmgast', 'title':'Helmgast AB'})
		print "Inserted default Helmgast publosher"
	else:
		hg_publisher = doc['_id']

	result = db.world.update({'publisher':{'$exists':False}},{'$set':{'publisher':hg_publisher}}, multi=True)
	print "Added helmgast as publisher on %i worlds" % result['n']