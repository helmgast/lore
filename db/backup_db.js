/* Usage: mongo <db_name> backup_db.js */

var now = new Date();
var iso_date = now.getFullYear() + "_" + (now.getMonth() < 10 ? "0" : "") + now.getMonth() + "_" + (now.getDate() < 10 ? "0" : "") + now.getDate();

var db_name = db.getName();
var db_dest = db_name + "_bak_" + iso_date;

printjson("Copying database " + db_name + " to " + db_dest);

//db.copyDatabase(db_name, db_dest);
