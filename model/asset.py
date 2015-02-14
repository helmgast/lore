"""
    model.asset
    ~~~~~~~~~~~~~~~~

    :copyright: (c) 2014 by Raconteur
"""
import mimetypes
import re
from raconteur import db
from model.misc import list_to_choices
from flask.ext.babel import lazy_gettext as _
from mongoengine.errors import ValidationError
from datetime import datetime
from user import User

from slugify import slugify
from misc import Choices
from world import ImageAsset


FileAccessType = Choices(
    public=_('Public'),
    product=_('Product'),
    user=_('User'))


class FileAsset(db.Document):
    slug = db.StringField(max_length=62)
    title = db.StringField(max_length=60, required=True, verbose_name=_('Title'))
    description = db.StringField(max_length=500, verbose_name=_('Description'))
    source_filename = db.StringField(max_length=60, required=True, verbose_name=_('File name'))
    attachment_filename = db.StringField(max_length=60, verbose_name=_('Attachment file name'))
    file_data = db.FileField(verbose_name=_('File data'))
    access_type = db.StringField(choices=FileAccessType.to_tuples(), required=True, verbose_name=_('Access type'))

    def clean(self):
        self.slug = slugify(self.title)

    def get_filename(self, user):
        return self.source_filename \
               % re.sub(r'@|\.', '_', user.email).lower() if self.user_exclusive else self.source_filename

    def get_attachment_filename(self):
        return self.attachment_filename if self.attachment_filename is not None else self.source_filename

    def get_mimetype(self):
        return mimetypes.guess_type(self.source_filename)[0]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s%s' % (self.title, ' [%s]' % self.access_type)
