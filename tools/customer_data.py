# coding=utf-8
import csv

from model.shop import *
from model.user import *


class Customer:
  def __init__(self, email, amnt1, amnt2, totamnt, perk, shipfee, paidshipfee, shouldpaid, balance, shipname, shipaddr,
               shipaddr2, shipcity, shipstate, shipzip, shipcountry, nameinbook):
    self.email = email
    self.amnt1 = amnt1
    self.amnt2 = amnt2
    self.totamnt = totamnt
    self.perk = perk
    self.shipfee = shipfee
    self.paidshipfee = paidshipfee
    self.shouldpaid = shouldpaid
    self.balance = balance
    self.shipname = shipname
    self.shipaddr = shipaddr
    self.shipaddr2 = shipaddr2
    self.shipcity = shipcity
    self.shipstate = shipstate
    self.shipzip = shipzip
    self.shipcountry = shipcountry
    self.nameinbook = nameinbook


def setup_customer():
  product_map = {
    "Stöd Eon IV": ["eon-iv-cf-stod"],
    "Grundboken + Spelpaketet": ["eon-iv-cf-grundbok", "eon-iv-cf-spelpaket", "eon-iv-cf-grundbok-digital",
                                 "eon-iv-cf-spelarbok-digital"],
    "Spelpaket-boken": ["eon-iv-cf-spelpaketbok"],
    "Helgon-boken": ["eon-iv-cf-helgonbok", "eon-iv-cf-spelpaket", "eon-iv-cf-grundbok-digital",
                     "eon-iv-cf-spelarbok-digital"],
    "Helmgast-boken": ["eon-iv-cf-helmgastbok", "eon-iv-cf-spelpaket", "eon-iv-cf-grundbok-digital",
                       "eon-iv-cf-spelarbok-digital"],
    "Mörkerherre-boken": ["eon-iv-cf-morkerherrebok", "eon-iv-cf-grundbok", "eon-iv-cf-spelpaket",
                          "eon-iv-cf-grundbok-digital", "eon-iv-cf-spelarbok-digital"],
    "Grundboken": ["eon-iv-cf-grundbok", "eon-iv-cf-grundbok-digital"],
    "Uppgradering till Helgon-boken": ["eon-iv-cf-helgonbok"],
    "Spelgruppspaketet": ["eon-iv-cf-grundbok", "eon-iv-cf-grundbok", "eon-iv-cf-grundbok",
                          "eon-iv-cf-spelpaket", "eon-iv-cf-grundbok-digital", "eon-iv-cf-spelarbok-digital"],
    "Xinu-boken": ["eon-iv-cf-xinuboken", "eon-iv-cf-helmgastbok", "eon-iv-cf-helgonbok", "eon-iv-cf-spelpaketbok",
                   "eon-iv-cf-spelpaket", "eon-iv-cf-grundbok-digital", "eon-iv-cf-spelarbok-digital"]
  }

  with open('tools/eon.csv', 'rb') as csvfile:
    customers = {}

    spamreader = csv.reader(csvfile, delimiter=';')
    for row in spamreader:
      email = row[0].lower()
      if not email in customers:
        customers[email] = {"raw": []}
      customers[email]["raw"].append(Customer(
        email,
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],
        row[6],
        row[7],
        row[8],
        row[9],
        row[10],
        row[11],
        row[12],
        row[13],
        row[14],
        row[15],
        row[16]))

    orders = []
    for email in customers.keys():
      customer_orders = customers[email]
      customer_user = None
      customer_address = None
      for order in customer_orders["raw"]:
        if not customer_user and order.shipname:
          customer_user = User(
            email=order.email,
            realname=order.shipname,
            location=order.shipcity
          )
        if not customer_address and order.shipname:
          customer_address = Address(
            name=order.shipname,
            street=order.shipaddr + (' ' + order.shipaddr2 if order.shipaddr2 else ''),
            zipcode=order.shipzip,
            city=order.shipcity,
            country=order.shipcountry
          )
      if not customer_user:
        customer_user = User(email=email)
      shippable_customer = customer_user and customer_address
      customer_orders["user"] = customer_user

      order_lines = {}
      for order in customer_orders["raw"]:
        order_products = product_map[order.perk]
        if not shippable_customer and order_products[0] != "eon-iv-cf-stod":
          raise Exception("Invalid purchas for customer: " + customer_user.email)

        for order_product in order_products:
          if order_product in order_lines:
            order_lines[order_product].quantity += 1
          else:
            db_product = Product.objects(slug=order_product).get()
            order_lines[order_product] = OrderLine(product=db_product, price=0)

      order = Order(user=customer_user,
            email=customer_user.email,
            order_lines=order_lines.values(),
            status=OrderStatus.paid,
            shipping_address=customer_address)

      orders.append(order)

    print "orders %d" % len(orders)
    for order in orders[1:]:
      order.user.save()
      order.save()
