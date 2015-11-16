from hashlib import sha1, md5
import random

# borrowing these methods, slightly modified, from django.contrib.auth
def get_hexdigest(salt, raw_password):
  return sha1((salt + unicode(raw_password)).encode('utf-8')).hexdigest()

def make_password(raw_password):
  salt = get_hexdigest(str(random.random()), str(random.random()))[:5]
  hsh = get_hexdigest(salt, raw_password)
  return '%s$%s' % (salt, hsh)

def check_password(raw_password, enc_password):
  if enc_password and raw_password:
    salt, hsh = enc_password.split('$', 1)
    return hsh == get_hexdigest(salt, raw_password)
  else:
    return False

def create_token(input_string, salt=u'e3af71457ddb83c51c43c7cdf6d6ddb3'):
  if not input_string:
      return ''
  return md5(input_string.strip().lower().encode('utf-8') + salt).hexdigest()

class BaseUser(object):
    def set_password(self, password):
      self.password = make_password(password)

    def check_password(self, password):
      return check_password(password, self.password)
