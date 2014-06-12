import csv
from auth import create_token


with open('C:/Users/Niklas/Downloads/all_emails.txt', 'rb') as csvfile:
  spamreader = csv.reader(csvfile, delimiter=' ', quotechar='|')
  for row in spamreader:
    print '%s;%s' % (row[0], create_token(row[0]))
