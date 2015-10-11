import re

def db_migrate(db, version=''):

	# This moves the field shipping_mobile to the right location
	for doc in db.order.find({'shipping_mobile':{'$exists':True}}):
		update = {'$unset':{'shipping_mobile':''}}
		# Remove old 07XXXXXXXX placeholders
		if not doc['shipping_mobile'] == '07XXXXXXXX':
			update['$set'] = {'shipping_address.mobile':doc['shipping_mobile']}
		results = db.order.update({'_id':doc['_id']}, update)

	# Shorten asset links to only slug/filename
	for doc in db.article.find({'content': {'$regex':']\(\/asset\/'}}):
		update = {'$set':{'content':re.sub(r']\(\/asset\/','](',doc['content'])}}
		results = db.article.update({'_id':doc['_id']}, update)

	# migrate double password
	#
