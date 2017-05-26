"""
    model.asset
    ~~~~~~~~~~~~~~~~

    :copyright: (c) 2014 by Helmgast AB
"""
import hashlib
import logging
import mimetypes
from StringIO import StringIO
from datetime import datetime

import requests
import os.path

from bson import ObjectId
from flask import request, current_app, g
from flask_babel import gettext, lazy_gettext as _

from misc import Document  # Enhanced document
from jinja2.filters import do_filesizeformat
from mongoengine import (StringField, DateTimeField, ImageField, URLField,
                         ReferenceField, ListField, FileField, IntField)
from mongoengine import ValidationError
from mongoengine.queryset import Q
from rfc6266 import parse_requests_response, ContentDisposition
from werkzeug.utils import secure_filename

from misc import Choices, reference_options, choice_options, numerical_options, distinct_options
from misc import slugify
from user import User
import magic

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

logger = current_app.logger if current_app else logging.getLogger(__name__)

FileAccessType = Choices(
    public=_('Public use'),  # Accessed by anyone
    hidden=_('Hidden'),  # Not shown in public listings but publicly accessed at hashed URL
    product=_('Product required'),  # Access given through some product
    user=_('User unique and product required'))  # Access given through some product, also user specific

allowed_mimetypes = {
    'application/pdf': 'pdf',
    'application/rtf': 'rtf',
    'application/zip': 'zip',
    'application/x-compressed-zip': 'zip',
    'application/msword': 'doc',
    'application/vnd.ms-excel': 'xls',
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/gif': 'gif',
    # 'image/svg+xml': 'svg',  # Disabled for time being, can be a security issue and more difficult to get width/height
    'text/plain': 'txt'}

FileType = Choices(
    image=_('Image'),
    file=_('File'),
    embed=_('Embed')
)


# Don't store any variations (e.g. thumbnails), generate on fly and cache outside

# On clean, if filedata in request, replace. If URL, and it has changed, fetch as file.
# Show icons as thumbnails or as icons

class FileAsset(Document):
    slug = StringField(max_length=62, unique=True)
    meta = {'indexes': ['slug', 'md5']}
    title = StringField(max_length=60, verbose_name=_('Title'))
    description = StringField(max_length=500, verbose_name=_('Description'))
    owner = ReferenceField(User, verbose_name=_('User'))
    file_data = FileField(verbose_name=_('File data'))
    access_type = StringField(choices=FileAccessType.to_tuples(), default=FileAccessType.public, verbose_name=_('Access type'))
    tags = ListField(StringField(max_length=30), verbose_name=_('Tags'))
    publisher = ReferenceField('Publisher', verbose_name=_('Publisher'))

    # Variables reflecting the underlying file object, updates on clean
    source_filename = StringField(max_length=60, verbose_name=_('Filename'))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_('Uploaded on'))
    content_type = StringField()
    length = IntField()
    width = IntField()
    height = IntField()
    md5 = StringField()

    # Optional data about source
    source_file_url = URLField(verbose_name=_('Source File URL'))
    source_page_url = URLField(verbose_name=_('Source Page URL'))
    # Alternative filename when downloaded
    # TODO DEPRECATE
    attachment_filename = StringField(max_length=60, verbose_name=_('Filename when downloading'))
    tmp_file_obj = None

    # TODO hack to avoid bug in https://github.com/MongoEngine/mongoengine/issues/1279
    def get_field_display(self, field):
        return self._BaseDocument__get_field_display(self._fields[field])

    def delete(self):
        if self.file_data:
            self.file_data.delete()
            self.file_data = None
        super(FileAsset, self).delete()

    def is_image(self):
        return self.content_type.startswith('image/')

    @classmethod
    def create_md5(cls, file_obj):
        block_size = 256*128
        md5 = hashlib.md5()
        for chunk in iter(lambda: file_obj.read(block_size), b''):
            md5.update(chunk)
        file_obj.seek(0)  # reset
        return md5.hexdigest()

    def aspect_ratio(self):
        return self.width/float(self.height) or 1.0

    def set_file(self, file_obj, filename, update_file=True):
        assert file_obj
        assert filename

        # Guess content type using file header instead of metadata
        content_type = magic.from_buffer(file_obj.read(1024), mime=True)
        file_obj.seek(0)
        if content_type not in allowed_mimetypes:
            raise ValidationError(
                gettext('Files of type %(mimetype)s are not allowed.', mimetype=content_type))

        # Check MD5 hash to avoid uploading duplicates
        md5 = FileAsset.create_md5(file_obj)
        if not md5:
            raise ValidationError("No MD5 from file_obj")

        # Check if we already have this file in data
        if self.file_data:
            # We have data, first check if
            existing_md5 = self.file_data.get().md5
            update_file = (md5 != existing_md5)  # Don't update file if md5 is same

        # Check if other files have same MD5
        existing = FileAsset.objects(md5=md5, id__ne=(self.id or ObjectId(b'notaobjectid')))  # needs to be 12 bytes
        if existing.count() > 0:
            raise ValidationError("Identical file already uploaded with name %s" % existing.get(0))

        # Check if valid image and get width/height if so
        if content_type.startswith('image/'):
            try:
                img = Image.open(file_obj)
                content_type = Image.MIME[img.format]
                # Check type again, may have changed
                if content_type not in allowed_mimetypes:
                    raise ValidationError("Not an allowed image type")
                self.width, self.height = img.size
            except Exception, e:
                raise ValidationError('Invalid image: %s' % e)
            file_obj.seek(0)
        else:
            self.width, self.height = 400, 400  # Default sizing for non images, which will get an SVG icon
        self.source_filename = filename
        self.content_type = content_type
        # Sync means we will re-create all fields but not actually change the file_obj
        if update_file:
            self.tmp_file_obj = file_obj

    @classmethod
    def make_slug(cls, filename, content_type):
        # Ensure we have a safe filename to use with proper extension
        name, ext = os.path.splitext(secure_filename(filename).lower())
        name = slugify(name)
        if not name:
            raise ValidationError("Couldn't create slug from filename %s" % filename)
        return name + '.' + allowed_mimetypes[content_type]

    def clean(self):
        new_file_obj = request.files.get('file_data', None)
        # This assumes there is a file upload
        if new_file_obj is not None and new_file_obj.filename:
            self.set_file(new_file_obj, filename=new_file_obj.filename)
        elif self.source_file_url and not self.file_data:
            r = requests.get(self.source_file_url)
            # Try to fetch correct filename based on Content-Disposition header or location
            # TODO this is a bug in rfc6266 package for handling a header like 'inline;filename=""'
            try:
                content_disp = parse_requests_response(r)
            except Exception as e:
                content_disp = ContentDisposition(location=self.source_file_url)  # Filename from URL
                logger.warning("Got exception %s when parsing fname of %s" % (e, self.source_file_url))
            fname = content_disp.filename_unsafe  # Will be made safe in set_file when creating slug
            self.set_file(StringIO(r.content), filename=fname)
            self.source_page_url = self.source_file_url

        if hasattr(self, '_changed_fields') and 'slug' in self._changed_fields:
            # Use user input slug but make it into slug format in case it wasn't
            self.slug = FileAsset.make_slug(self.slug, self.content_type)
        else:
            # Regenerate slug
            self.slug = FileAsset.make_slug(self.source_filename, self.content_type)

        if self.tmp_file_obj:
            # We have received a file obj
            self.file_data.replace(self.tmp_file_obj, content_type=self.content_type, filename=self.source_filename)
            self.tmp_file_obj = None

        fs = self.file_data.get()
        self.length = fs.length
        self.created_date = fs.upload_date
        self.md5 = fs.md5
        if not self.owner:  # Don't overwrite owner as it may mean admins overwrite original uploader
            self.owner = g.user

    def get_attachment_filename(self):
        filename = self.attachment_filename if self.attachment_filename is not None else self.source_filename
        return filename

    def is_public(self):
        return self.access_type == FileAccessType.public

    def file_data_exists(self):
        return self.file_data.grid_id is not None

    def get_mimetype(self):
        return mimetypes.guess_type(self.source_filename)[0]

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __unicode__(self):
        return u'%s' % (self.title or self.slug)


FileAsset.owner.filter_options = reference_options('owner', User)
# Use same way to format filesize as jinja by calling that filter directly
FileAsset.length.filter_options = numerical_options('length', spans=[100000, 1000000, 10000000], labels=[
    _('Less than %(val)s', val=do_filesizeformat(100000)),
    _('Less than %(val)s', val=do_filesizeformat(1000000)),
    _('Less than %(val)s', val=do_filesizeformat(10000000)),
    _('More than %(val)s', val=do_filesizeformat(10000000))])
FileAsset.tags.filter_options = distinct_options('tags', FileAsset)
FileAsset.access_type.filter_options = choice_options('access_type', FileAsset.access_type.choices)

MimeTypes = Choices({
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'image/gif': 'GIF'
})
IMAGE_FILE_ENDING = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/gif': 'gif'}


class ImageAsset(Document):
    slug = StringField(primary_key=True, min_length=5, max_length=60, verbose_name=_('Slug'))
    meta = {'indexes': ['slug']}
    image = ImageField(thumbnail_size=(300, 300, False), required=True)
    source_image_url = URLField()
    source_page_url = URLField()
    tags = ListField(StringField(max_length=30))
    mime_type = StringField(choices=MimeTypes.to_tuples(), required=True)
    creator = ReferenceField(User, verbose_name=_('Creator'))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_('Created date'))
    title = StringField(min_length=1, max_length=60, verbose_name=_('Title'))
    description = StringField(max_length=500, verbose_name=_('Description'))

    def __unicode__(self):
        return u'%s' % self.slug

    # Executes before saving
    def clean(self):
        if self.title:
            parts = secure_filename(self.title).rsplit('.', 1)
            slug = parts[0]
        else:
            slug = self.id
        if not slug:
            raise ValueError('Cannot make slug from either title %s or id %s' % (self.title, self.id))
        new_end = IMAGE_FILE_ENDING[self.mime_type]
        new_slug = slug + '.' + new_end
        existing = len(ImageAsset.objects(Q(slug__endswith='__' + new_slug) or Q(slug=new_slug)))
        if existing:
            new_slug = "%i__%s.%s" % (existing + 1, slug, new_end)
        self.slug = new_slug

