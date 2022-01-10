var prodNum = "KDL-220xxxl";
var prodId = db.getCollection('product').findOne({product_number: prodNum})._id
db.getCollection('product').find({_id: prodId})
db.getCollection('order').find({"order_lines.product":prodId})