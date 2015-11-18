"""
    model.asset
    ~~~~~~~~~~~~~~~~

    :copyright: (c) 2014 by Helmgast AB
"""
import mimetypes
import re
from mongoengine import ValidationError
from datetime import datetime
from slugify import slugify
from werkzeug.utils import secure_filename
from mongoengine.queryset import Q
import requests
from StringIO import StringIO
import imghdr

from fablr.app import db
from user import User
from flask.ext.babel import gettext, lazy_gettext as _
from misc import Choices
from flask import request


FileAccessType = Choices(
    # Accessed by anyone
    public=_('Public use'),
    # Access given through some product
    product=_('Product required'),
    # Access given through some product, also user specific
    user=_('User unique and product required'))

allowed_mimetypes = [
    'application/pdf',
    'application/rtf',
    'application/zip',
    'application/x-compressed-zip',
    'image/jpeg',
    'image/png',
    'text/plain']

# New unified Asset
# filename (unique)
# original_name (filename or URL)
# source (URL)
# title
# description
# owner
# gridfile (includes filename, upload date, mime, etc)
# access_type (public, personal, personal & fingerprinted)
# variation (different sized image, if supported). Use Pillow to generate
# variation on the fly, but ensure it's cached.

# On clean, if filedata in request, replace. If URL, and it has changed, fetch as file.
# Show icons as thumbnails or as icons

class FileAsset(db.Document):
    slug = db.StringField(max_length=62)
    title = db.StringField(max_length=60, required=True, verbose_name=_('Title'))
    description = db.StringField(max_length=500, verbose_name=_('Description'))
    # Internal filename
    source_filename = db.StringField(max_length=60, verbose_name=_('Filename'))
    # Alternative filename when downloaded
    attachment_filename = db.StringField(max_length=60, verbose_name=_('Filename when downloading'))
    # Actual file
    file_data = db.FileField(verbose_name=_('File data'))
    # How the file might be accessed
    access_type = db.StringField(choices=FileAccessType.to_tuples(), required=True, verbose_name=_('Access type'))


    def clean(self):
        request_file_data = request.files.get('file_data', None)
        # This assumes there is a file upload
        if request_file_data is not None and request_file_data.filename:
            if request_file_data.mimetype not in allowed_mimetypes:
                raise ValidationError(
                    gettext('Files of type %(mimetype)s are not allowed.', mimetype=request_file_data.mimetype))
            # File is present, save to GridFS
            self.file_data.replace(request_file_data, content_type=request_file_data.mimetype, filename=request_file_data.filename)
            self.source_filename = request_file_data.filename
            if not self.attachment_filename:
                self.attachment_filename = self.source_filename
        name, ext = secure_filename(self.source_filename).lower().rsplit('.',1)
        self.slug = slugify(name)+'.'+ext


    def get_attachment_filename(self):
        filename = self.attachment_filename if self.attachment_filename is not None else self.source_filename
        return filename

    def is_public(self):
        return self.access_type == FileAccessType.public

    def file_data_exists(self):
        return self.file_data.grid_id is not None

    def get_mimetype(self):
        return mimetypes.guess_type(self.source_filename)[0]

    def access_type_name(self):
        return FileAccessType[self.access_type]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s%s' % (self.title, ' [%s]' % self.access_type)

MimeTypes = Choices({
  'image/jpeg': 'JPEG',
  'image/png':'PNG',
  'image/gif':'GIF'
  })
IMAGE_FILE_ENDING = {'image/jpeg':'jpg','image/png':'png','image/gif':'gif'}
class ImageAsset(db.Document):
  slug = db.StringField(primary_key=True, min_length=5, max_length=60, verbose_name=_('Slug'))
  meta = {'indexes': ['slug']}
  image = db.ImageField(thumbnail_size=(300,300,False), required=True)
  source_image_url = db.URLField()
  source_page_url = db.URLField()
  tags = db.ListField(db.StringField(max_length=30))
  mime_type = db.StringField(choices=MimeTypes.to_tuples(), required=True)
  creator = db.ReferenceField(User, verbose_name=_('Creator'))
  created_date = db.DateTimeField(default=datetime.utcnow, verbose_name=_('Created date'))
  title = db.StringField(min_length=1, max_length=60, verbose_name=_('Title'))
  description = db.StringField(max_length=500, verbose_name=_('Description'))

  def __unicode__(self):
    return u'%s' % self.slug

  # Executes before saving
  def clean(self):
    if self.title:
      slug, end = secure_filename(self.title).rsplit('.', 1)
      if len(end)>4:
        slug = slug+end # end is probably not a file ending
    else:
      slug = self.id
    if not slug:
      raise ValueError('Cannot make slug from either title %s or id %s' % (self.title, self.id))
    new_end = IMAGE_FILE_ENDING[self.mime_type]
    new_slug = slug+'.'+new_end
    existing = len(ImageAsset.objects(Q(slug__endswith='__'+new_slug) or Q(slug=new_slug)))
    if existing:
      new_slug = "%i__%s.%s" % (existing+1, slug, new_end)
    self.slug = new_slug

  def make_from_url(self, image_url, source_url=None):
    # TODO use md5 to check if file already downloaded/uploaded
    r = requests.get(image_url)
    file = StringIO(r.content)
    self.mime_type = r.headers['Content-Type']
    self.source_image_url = image_url
    self.source_page_url = source_url
    fname = image_url.rsplit('/',1)[-1]
    self.title = self.title or fname
    self.image.put(file, content_type=self.mime_type, filename=fname)
    logger.info("Fetched %s image from %s to DB", self.image.format, image_url)

  def make_from_file(self, file):
    # block_size=256*128
    # md5 = hashlib.md5()
    # for chunk in iter(lambda: file.read(block_size), b''):
    #      md5.update(chunk)
    # print md5.hexdigest()
    # file.seek(0) # reset
    self.mime_type = file.mimetype if file.mimetype else mimetypes.guess_type(file.filename)[0]
    self.image.put(file, content_type=self.mime_type, filename=file.filename)
