# coding=utf-8
# import csv
from auth import create_token

# print create_token("niklas@helmgast.se")
# print create_token("martin@helmgast.se")
# print create_token("marco@helmgast.se")
# print create_token("petter@helmgast.se")
# print create_token("anton@helmgast.se")
# print create_token("stormflare74@gmail.com")
# print create_token("perolus@gmail.com", salt='Jag är bara en störig gubbjävel i hörnet')
# print create_token("Daniel788@live.se", salt='Jag är bara en störig gubbjävel i hörnet')
# print create_token("daniel788@live.se")
# print create_token("niklas.frojd@gmail.com")
# print slugify("Eon 3 - Spelledarens guide")
# print slugify("Eon 3 - Spelarbok")
# print slugify("Eon 3 - Mystik & Magi")
# print slugify("Äventyrarens handbok")
# print create_token("daniele788@hotmail.com")
# print create_token("perolus@gmail.com")
# print create_token("styrelse@daaksord.org")
# print create_token("rasmus.liljeholm@live.se")
# print u'\xe4'

# print make_password(u'äver')
# print '\xc3'


def show_token(tokens):
    for token in tokens:
        print("%s\t%s\t%s" % (
            token, create_token(token, salt='Jag är bara en störig gubbjävel i hörnet'), create_token(token)))


show_token(["carljohanstrom@gmail.com", "kim.neogames@gmail.com", "dan.storafiler@gmail.com", "ola.jentzsch@gmail.com",
            "holgersson.f@gmail.com", "raecer@gmail.com", "dark_storm84@hotmail.com", "dr45tr@gmail.com",
            "niklas@helmgast.se", "martin@helmgast.se", "marco@helmgast.se", "petter@helmgast.se", "anton@helmgast.se",
            "paul@helmgast.se"])

# with open('C:/Users/Niklas/Downloads/all_emails.txt', 'rb') as csvfile:
#   spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
#   for row in spamreader:
#     print '%s;%s' % (row[0], create_token(row[0]))
