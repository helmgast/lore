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
  stod = Product(title='Eon IV - Stöd',
                 description='Du visar ditt stöd för oss och rollspelshobbyn och får för det ett tack i boken.',
                 publisher='Helmgast AB',
                 family='Eon',
                 type=ProductTypes.book,
                 price=5,
                 currency=Currencies.eur,
                 status=ProductStatus.available).save()
  namn_i_boken = Product(title='Eon IV - Namn i boken',
                         description='Som tack för att du crowdfundat får du ditt namn i boken.',
                         publisher='Helmgast AB',
                         family='Eon',
                         type=ProductTypes.digital,
                         price=0,
                         currency=Currencies.eur,
                         status=ProductStatus.available,
                         acknowledgement=True).save()
  namn_i_boken_st = Product(title='Eon IV - Helgonnamn i boken',
                            description='Som tack för att du crowdfundat får du ditt namn i boken skrivet som ett helgon (S:t).',
                            publisher='Helmgast AB',
                            family='Eon',
                            type=ProductTypes.digital,
                            price=0,
                            currency=Currencies.eur,
                            status=ProductStatus.available,
                            acknowledgement=True).save()
  grundboken = Product(title='Eon IV - Grundboken',
                       description='Grundbok för Eon IV på 286 sidor',
                       publisher='Helmgast AB',
                       family='Eon',
                       type=ProductTypes.book,
                       price=45,
                       currency=Currencies.eur,
                       status=ProductStatus.available).save()
  grundboken_spelpaketet = Product(title='Eon IV - Grundboken + Spelpaketet',
                                   description='Grundbok för Eon IV med Spelpaketet',
                                   publisher='Helmgast AB',
                                   family='Eon',
                                   type=ProductTypes.book,
                                   price=69,
                                   currency=Currencies.eur,
                                   status=ProductStatus.available).save()
  spelpaketboken = Product(title='Eon IV - Spelpaketboken',
                           description='Få PDF:material från spelpaketet samlat och tryckt i en crowdfunder-unik bok och hemskickat till dig.',
                           publisher='Helmgast AB',
                           family='Eon',
                           type=ProductTypes.book,
                           price=39,
                           currency=Currencies.eur,
                           status=ProductStatus.available).save()
  spelgruppspaketet = Product(title='Eon IV - Spelgruppspaketet',
                              description='Grundbok för Eon IV i 3 exemplar',
                              publisher='Helmgast AB',
                              family='Eon',
                              type=ProductTypes.book,
                              price=147,
                              currency=Currencies.eur,
                              status=ProductStatus.available).save()
  helgonboken = Product(title='Eon IV - Helgonboken',
                        description='Grundbok för Eon IV i helgonutgåva',
                        publisher='Helmgast AB',
                        family='Eon',
                        type=ProductTypes.book,
                        price=119,
                        currency=Currencies.eur,
                        status=ProductStatus.available).save()
  helmgastboken = Product(title='Eon IV - Helmgastboken',
                          description='Grundbok för Eon IV i helmgastutgåva',
                          publisher='Helmgast AB',
                          family='Eon',
                          type=ProductTypes.book,
                          price=99,
                          currency=Currencies.eur,
                          status=ProductStatus.available).save()
  morkerherreboken = Product(title='Eon IV - Mörkerherreboken',
                             description='Grundbok för Eon IV i mörkerherreutgåva',
                             publisher='Helmgast AB',
                             family='Eon',
                             type=ProductTypes.book,
                             price=299,
                             currency=Currencies.eur,
                             status=ProductStatus.available).save()
  xinuboken = Product(title='Eon IV - Xinuboken',
                      description='Grundbok för Eon IV i den enda Xinuutgåvan',
                      publisher='Helmgast AB',
                      family='Eon',
                      type=ProductTypes.book,
                      price=45,
                      currency=Currencies.eur,
                      status=ProductStatus.available).save()
  grundboken_digital = Product(title='Eon IV - Grundbok PDF',
                               description='PDF för Grundboken',
                               publisher='Helmgast AB',
                               family='Eon',
                               type=ProductTypes.digital,
                               price=0,
                               currency=Currencies.eur,
                               status=ProductStatus.ready_for_download).save()
  spelpaketet_digital = Product(title='Eon IV - Spelpaketet PDF',
                                description='PDF för Spelpaketet',
                                publisher='Helmgast AB',
                                family='Eon',
                                type=ProductTypes.digital,
                                price=0,
                                currency=Currencies.eur,
                                status=ProductStatus.available).save()
  product_map = {
    "Stöd Eon IV": [stod],
    "Grundboken + Spelpaketet": [grundboken_spelpaketet, grundboken_digital, spelpaketet_digital, namn_i_boken],
    "Spelpaket-boken": [spelpaketboken],
    "Helgon-boken": [helgonboken, grundboken_digital, spelpaketet_digital, namn_i_boken_st],
    "Helmgast-boken": [helmgastboken, grundboken_digital, spelpaketet_digital, namn_i_boken],
    "Mörkerherre-boken": [morkerherreboken, grundboken_digital, spelpaketet_digital, namn_i_boken],
    "Grundboken": [grundboken, grundboken_digital, namn_i_boken],
    "Uppgradering till Helgon-boken": [],
    "Spelgruppspaketet": [spelgruppspaketet, grundboken_digital, spelpaketet_digital, namn_i_boken, namn_i_boken, namn_i_boken],
    "Xinu-boken": [xinuboken, spelpaketboken, grundboken_digital, spelpaketet_digital, namn_i_boken]
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
        if not shippable_customer and order.perk != "Stöd Eon IV":
          raise Exception("Invalid purchase for customer: " + customer_user.email)

        for order_product in order_products:
          if order_product in order_lines:
            order_lines[order_product].quantity += 1
          else:
            order_lines[order_product] = OrderLine(product=order_product, price=order_product.price)

      order_sum = 0
      order_items = 0
      for order_line in order_lines.values():
        order_sum += order_line.quantity * order_line.price
        order_items += order_line.quantity

      order = Order(user=customer_user,
            email=customer_user.email,
            order_lines=order_lines.values(),
            total_items=order_items,
            total_price=order_sum,
            status=OrderStatus.paid,
            shipping_address=customer_address)

      orders.append(order)

    print "orders %d" % len(orders)
    for order in orders[1:]:
      order.user.save()
      order.save()
