// Orders attached to deleted users, should instead go to active users
//DBQuery.shellBatchSize = 500; // required to workaround robo3t limitation on number of results
db.user.aggregate([
    { $match: {status:"deleted"}}
    ,{
        $lookup:
           {
               from: "order",
               localField: "_id",
               foreignField: "user",
               as: "orders"
           }
   }
   ,{ $addFields: {orderCount: {$size: "$orders"}}}
   ,{ $match: {orderCount: {$gte:1}}}
])