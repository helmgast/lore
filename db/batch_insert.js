/* Usage: mongo <db_name> */
/* This is just a sample file */

//db.article.insert( { _id: 10, type: "misc", item: "card", qty: 15 } )

var sample_world = db.world.findOne();
printjson(sample_world.title);


var sample_data = {
    "slug": "ljusbringaren-bild",
    "type": 1,
    "world": sample_world.id,
    "creator": ObjectId("531b1385b7426f25a8f60d25"),
    "created_date": ISODate(),
    "title": "Ljusbringaren bild",
    "content": "No content",
    "status": 0,
    "imagedata": {
        "image": ObjectId("531b1388b7426f25a8f60d33"),
        "source_image_url": "http://kaigon.se/wiki/images/6/6b/Ljusets_son.jpg",
        "mime_type": "image/jpeg"
    },
    "relations": [ ]
};
