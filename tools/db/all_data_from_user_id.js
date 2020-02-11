var objId = ObjectId("539da22f24b9822f7934e7ad");

db.getCollection('article').find({creator:objId});
db.getCollection('event').find({user:objId});
db.getCollection('order').find({user:objId});
