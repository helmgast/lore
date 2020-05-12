var fileasset = ObjectId("5df375df293860bc2053ad02");

var gridfile = db.file_asset.findOne({_id:fileasset}).file_data
db.fs.chunks.remove({files_id:gridfile})
db.fs.files.remove({_id:gridfile})
db.file_asset.remove({_id:fileasset})


