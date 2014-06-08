import csv
from model.shop import *
from model.user import *

class customer:
    email = ""
    amnt1 = ""
    amnt2 = ""
    totamnt = ""
    perk = ""
    shipfee = ""
    paidshipfee = ""
    shouldpaid = ""
    balance = ""
    shipname = ""
    shipaddr = ""
    shipaddr2 = ""
    shipcity = ""
    shipstate = ""
    shipzip = ""
    shipcountry = ""
    nameinbook = ""
    comment = ""
    emailcomment = ""

    def __init__(self, email, amnt1, amnt2, totamnt, perk, shipfee, paidshipfee, shouldpaid, balance, shipname, shipaddr, shipaddr2, shipcity, shipstate, shipzip, shipcountry, nameinbook, comment, emailcomment):
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
      self.comment = comment
      self.emailcomment = emailcomment

with open('eon.csv', 'rb') as csvfile:
  field_names = ['Email', 'Amount 1', 'Amount 2', 'Total Amount', 'Perk', 'Shipping Fee', 'Shipping Fee Paid', 'Should have paid', 'Payment balance', 'Shipping Name', 'Shipping Address', 'Shipping Address 2', 'Shipping City', 'Shipping State', 'Shipping Zip', 'Shipping Country', 'Name in Book', 'Comment', 'Email Comment' ]
  
  customers = []
  orders = []
  users = []
  orderlines = []
  
  spamreader = csv.DictReader(csvfile, fieldnames=field_names)
  for row in spamreader:
    tmp  = customer(
        row[u'Email'],
        row[u'Amount 1'],
        row[u'Amount 2'],
        row[u'Total Amount'],
        row[u'Perk'],
        row[u'Shipping Fee'],
        row[u'Shipping Fee Paid'],
        row[u'Should have paid'],
        row[u'Payment balance'],
        row[u'Shipping Name'],
        row[u'Shipping Address'],
        row[u'Shipping Address 2'],
        row[u'Shipping City'],
        row[u'Shipping State'],
        row[u'Shipping Zip'],
        row[u'Shipping Country'],
        row[u'Name in Book'],
        row[u'Comment'],
        row[u'Email Comment'])
    customers.append(tmp)

  for customer in customers:
    usr = User(
        username=customer.email.partition('@')[0],
        email=customer.email,
        realname=customer.shipname,
        location=customer.shipcity + ", " + customer.shipcountry
        )

  # Iterate over each customer with identical email, create orderline for each

  # orderlines.append(orderline)
  # Append all orderlines to the Order object
    order = Order(
        user=usr.username,
        email=usr.email,
        order_lines=orderlines,
        total_items="", # Count amount in each orderline
        total_price="", # Count price from each orderline
        created="",
        updated="",
        status="",
        shipping_address="" # Concatenate all shipping related attributes
        )

      # Save each order in list
    orders.append(order)
