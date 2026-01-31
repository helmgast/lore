// 1) find product id
const prod = db.product.findOne({ product_number: "KH-044" }, { _id: 1 });
if (!prod) { print("Product not found"); }

// 2) aggregate orders
db.order.aggregate([
  { $unwind: "$order_lines" },
  { $match: { "order_lines.product": prod._id } },
  { $group: {
      _id: "$order_lines.product",
      totalQuantity: { $sum: "$order_lines.quantity" },
      ordersCount: { $sum: 1 }
  } }
]);