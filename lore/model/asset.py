"""
    model.asset
    ~~~~~~~~~~~~~~~~

    :copyright: (c) 2014 by Helmgast AB
"""
import hashlib
import logging
import mimetypes
from io import BytesIO, StringIO
from datetime import datetime

import requests
import os.path
from urllib.parse import urlparse, quote, unquote

from bson import ObjectId
from flask import request, current_app, g, url_for
from flask_babel import gettext, lazy_gettext as _

from .misc import Document  # Enhanced document
from jinja2.filters import do_filesizeformat
from mongoengine import (
    StringField,
    DateTimeField,
    ImageField,
    URLField,
    ReferenceField,
    ListField,
    FileField,
    IntField,
    NULLIFY,
    DENY,
    CASCADE,
)
from mongoengine import ValidationError, EmbeddedDocument
from mongoengine.queryset import Q
from werkzeug.utils import secure_filename

from .misc import Choices, reference_options, choice_options, numerical_options, distinct_options
from .misc import slugify
from .user import User, Group
import magic
import re
from lore.model.misc import extract

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

logger = current_app.logger if current_app else logging.getLogger(__name__)

FileAccessType = Choices(
    public=_("Public use"),  # Accessed by anyone
    hidden=_("Hidden"),  # Not shown in public listings but publicly accessed at hashed URL
    product=_("Product required"),  # Access given through some product
    user=_("User unique and product required"),
)  # Access given through some product, also user specific

allowed_mimetypes = {
    "application/pdf": "pdf",
    "application/rtf": "rtf",
    "application/zip": "zip",
    "application/x-compressed-zip": "zip",
    "application/msword": "doc",
    "application/vnd.ms-excel": "xls",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    # 'image/svg+xml': 'svg',  # Disabled for time being, can be a security issue and more difficult to get width/height
    "text/plain": "txt",
}


def guess_content_type(filename):
    name, ext = os.path.splitext(filename)
    if ext:
        for k, v in allowed_mimetypes.items():
            if ext.endswith(v):
                return k
    return None

# title - text description of asset
# filename - e.g. the slug, automatically created from URL
# source_url - remote source
# mime_type
# resolution
# filesize

# Access rules for FileAssets depends on their parent document, with the addition that access may require to have a product.

# Image formats:
# Wide: 2400px x >400px, aspect >2:1
# Center: 1600px x any, any aspect
# Card: 800px x 800-1120px, aspect 1:1 to 5:7

# Default URL for downloading a file would be
# :publisher.tld/:world/:article/:filename.ext
# e.g. helmgast.se/eon/rollformular/rollformular.pdf
# but the old format is :host.tld/asset/(link|download)/:slug and this still needs to work

# Editor behaviour
# We have an article/world/product and want to add some images.
# We can type an image link directly into the content. --> Will turn into a FileAsset on the article
# We can drag a file directly on the content --> Will upload it to default source and turn it into a FileAsset on the article
# We can click "Add file asset". It will popup a modal where we can enter a URL, upload, or pick from Google.
# We can click an existing file asset. It will show a modal where we can rename the asset and see different formats it can be represented in.


def sniff_remote_file(url):
    headers = {"Range": "bytes=0-100"}
    r = requests.get(url, headers=headers)
    content_type = r.headers.get("content-type", "")
    # Content-Disposition	examples
    # attachment;filename="anon_2d-1200px.png";filename*=UTF-8''anon_2d-1200px.png
    # inline;filename="v_rldstr_dets-grenar-20200423.pdf";filename*=UTF-8\'\'v%C3%A4rldstr%C3%A4dets-grenar-20200423.pdf
    fname, fnameutf = extract(r.headers.get("content-disposition", ""), r'filename="(.*?)";(?:filename\*=UTF-8\'\'([^;]+))?', groups=2)
    fnameutf = unquote(fnameutf)
    fname = fnameutf or fname or os.path.basename(urlparse(url).path)
    length = int(extract(r.headers.get("content-range", ""), r"bytes \d+-\d+\/(.*)", 0))
    width, height = (0, 0)
    try:
        img = Image.open(BytesIO(r.content))
        width, height = img.size
    except Exception as e:
        pass
    return {"fname": fname, "content_type": content_type, "w": width, "h": height, "length": length, "response": r}


class Attachment(EmbeddedDocument):
    source_url = URLField(verbose_name=_("Source File URL"))
    filename = StringField(
        max_length=62
    )  # Same as previous slug for FileAsset, so needs to be unique also compared to FileAsset slugs
    title = StringField(max_length=62)
    caption = StringField(max_length=500, verbose_name=_("Description"))
    access_type = StringField(
        choices=FileAccessType.to_tuples(), default=FileAccessType.public, verbose_name=_("Access type")
    )
    file_data = FileField(verbose_name=_("File data"))

    # position =  what positions and format to use the assets in

    # Automatically set, not user input
    content_type = StringField()
    width = IntField()
    height = IntField()
    downloads = IntField()

    def is_image(self):
        return self.content_type.startswith("image/")

    def image_url(self, *options):
        """Returns an image url that is generated to a certain format, e.g. a thumbnail. If the original file is
        not an image, this will instead generate a suitable file preview such as an icon."""
        pass

    def aspect_ratio(self):
        pass

    def srcset(self, *options):
        """Returns a srcset representing several image formats representing this file"""

    def dl_url(self, *options):
        """Returns original asset download URL, if the user passes an authorization check"""
        pass

    def clean(self):
        """If we get a new URL, we'll need to download it to get it's content type and width/height. Or we get this through Cloudinary?"""
        # TODO may be risky/slow to attempt and download large remote files. a HEAD works quickly for content type but not for image size.
        # So we should not blindly attempt to set these things.
        pass


def get_google_urls(url):
    g_id = extract(url, r"https:\/\/drive.google\.com\/(?:open\?id=|file\/d\/|thumbnail\?sz=.+?&id=|uc\?export=download&id=|uc\?export=view&id=)([^&\/]+)")
    if not g_id:
        return {}
    urls = {"google_id": g_id}
    urls["direct"] = f"https://drive.google.com/uc?export=view&id={g_id}"
    urls["dl"] = f"https://drive.google.com/uc?export=download&id={g_id}"
    urls["view"] = f"https://drive.google.com/open?id={g_id}"
    return urls


class FileAsset(Document):
    slug = StringField(max_length=99, unique=True)
    meta = {
        "indexes": ["slug", "md5", {"fields": ["$slug", "$title", "$description", "$tags"]}],
        # 'auto_create_index': True
    }

    title = StringField(max_length=99, verbose_name=_("Title"))
    description = StringField(max_length=500, verbose_name=_("Description"))
    owner = ReferenceField(User, reverse_delete_rule=NULLIFY, verbose_name=_("User"))
    file_data = FileField(verbose_name=_("File data"))
    access_type = StringField(
        choices=FileAccessType.to_tuples(), default=FileAccessType.public, verbose_name=_("Access type")
    )
    tags = ListField(StringField(max_length=60), verbose_name=_("Tags"))
    publisher = ReferenceField("Publisher", verbose_name=_("Publisher"))

    # Variables reflecting the underlying file object, updates on clean
    source_filename = StringField(max_length=60, verbose_name=_("Filename"))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_("Uploaded on"))
    content_type = StringField()
    length = IntField()
    width = IntField()
    height = IntField()
    md5 = StringField()

    # Optional data about source
    source_file_url = URLField(verbose_name=_("Source File URL"))
    source_page_url = URLField(verbose_name=_("Source Page URL"))
    # Alternative filename when downloaded
    # TODO DEPRECATE
    attachment_filename = StringField(max_length=60, verbose_name=_("Filename when downloading"))
    tmp_file_obj = None

    # def delete(self):
    #     if self.file_data:
    #         self.file_data.delete()
    #         self.file_data = None
    #     super(FileAsset, self).delete(clean=False)

    def is_image(self):
        return self.content_type.startswith("image/")

    @classmethod
    def create_md5(cls, file_obj):
        block_size = 256 * 128
        md5 = hashlib.md5()
        for chunk in iter(lambda: file_obj.read(block_size), b""):
            md5.update(chunk)
        file_obj.seek(0)  # reset
        return md5.hexdigest()

    def feature_url(self, **kwargs):
        crop = kwargs.pop("crop", None)
        transform = kwargs.pop("transform", "")
        cloudinary = current_app.config.get("CLOUDINARY_DOMAIN")
        if cloudinary:
            if self.source_file_url:
                url = self.source_file_url
            else:
                kwargs["_external"] = True
                if not current_app.config["PRODUCTION"]:
                    logger.debug("Force swapping URL to use helmgast.se instead of test")
                    kwargs["pub_host"] = "helmgast.se"
                url = url_for("image_thumb", slug=self.slug, **kwargs)
            if crop and len(crop) >= 2:
                # https://res.cloudinary.com/demo/image/upload/w_250,h_250,c_limit/sample.jpg
                crop_type = "lfill" if len(crop) != 3 else crop[2]
                transform = f"w_{crop[0]},h_{crop[1]},c_{crop_type},g_auto/"
            if transform and not transform.endswith("/"):
                transform += "/"
            # Google Drive URLs doesn't resolve for Cloudinary, but the thumb might
            feature_url = f"https://res.cloudinary.com/{cloudinary}/image/fetch/{transform}{quote(url)}"
            return feature_url
        else:
            return url_for("image_thumb", slug=self.slug, **kwargs)

    @property
    def thumb_url(self):
        return self.feature_url(transform="w_250,h_250,c_limit")

    def aspect_ratio(self):
        if self.height:
            return self.width / self.height
        else:
            return 1.0

    def set_file(self, file_obj, filename, update_file=True):
        assert file_obj
        assert filename

        # Guess content type using file header instead of metadata
        content_type = magic.from_buffer(file_obj.read(1024), mime=True)
        file_obj.seek(0)
        if content_type not in allowed_mimetypes:
            raise ValidationError(gettext("Files of type %(mimetype)s are not allowed.", mimetype=content_type))

        # Check MD5 hash to avoid uploading duplicates
        md5 = FileAsset.create_md5(file_obj)
        if not md5:
            raise ValidationError("No MD5 from file_obj")

        # Check if we already have this file in data
        if self.file_data:
            # We have data, first check if
            existing_md5 = self.file_data.get().md5
            update_file = md5 != existing_md5  # Don't update file if md5 is same

        # Check if other files have same MD5
        existing = FileAsset.objects(md5=md5, id__ne=(self.id or ObjectId(b"notaobjectid")))  # needs to be 12 bytes
        if existing.count() > 0:
            raise ValidationError("Identical file already uploaded with name %s" % existing.get(0))

        # Check if valid image and get width/height if so
        if content_type.startswith("image/"):
            try:
                img = Image.open(file_obj)
                content_type = Image.MIME[img.format]
                # Check type again, may have changed
                if content_type not in allowed_mimetypes:
                    raise ValidationError("Not an allowed image type")
                self.width, self.height = img.size
            except Exception as e:
                raise ValidationError("Invalid image: %s" % e)
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
        return name + "." + allowed_mimetypes[content_type]

    def clean(self):
        self.length = 0
        self.created_date = datetime.utcnow()
        self.md5 = ""

        new_file_obj = request.files.get("file_data", None) if request else None
        # This assumes there is a file upload
        if new_file_obj is not None and new_file_obj.filename:
            self.set_file(new_file_obj, filename=new_file_obj.filename)
        elif self.source_file_url and self.source_file_url.startswith(
            "https://res.cloudinary.com/helmgast/image/upload/"
        ):
            # A cloudinary URL
            return
        elif (self.source_file_url and not self.file_data) and (not self.source_filename or self.content_type) :
            metadata = sniff_remote_file(self.source_file_url)
            self.source_filename = metadata["fname"]
            self.content_type = metadata["content_type"]
            if self.content_type not in allowed_mimetypes:
                raise ValidationError(
                    f"Asset {self.source_file_url} has forbidden content type {self.content_type}. "
                    + f"Check URL for correctness. Response: {metadata['response']}"
                )
            self.width, self.height = metadata["w"], metadata["h"]
            self.length = metadata["length"]
        if not self.source_filename or not self.content_type:
            raise ValidationError("No filename or content type created for FileAsset, aborting")

        if hasattr(self, "_changed_fields") and "slug" in self._changed_fields:
            # Use user input slug but make it into slug format in case it wasn't
            self.slug = FileAsset.make_slug(self.slug, self.content_type)
        elif not self.slug:
            # Generate slug first time
            self.slug = FileAsset.make_slug(self.title or self.source_filename, self.content_type)

        if self.tmp_file_obj:
            # We have received a file obj
            self.file_data.replace(self.tmp_file_obj, content_type=self.content_type, filename=self.source_filename)
            self.tmp_file_obj = None

        fs = self.file_data.get() if self.file_data else None
        if fs:
            self.length = fs.length
            self.created_date = fs.upload_date
            self.md5 = fs.md5
        if not self.md5:
            self.md5 = str(datetime.timestamp(datetime.utcnow()))

        if FileAsset.objects(slug=self.slug, id__ne=(self.id or ObjectId(b"notaobjectid"))).count() > 0:
            self.slug = "{md5}-{slug}".format(md5=self.md5, slug=self.slug)

        if (
            not self.owner and g and getattr(g, "user", None)
        ):  # Don't overwrite owner as it may mean admins overwrite original uploader
            self.owner = g.user

    def get_attachment_filename(self):
        filename = self.attachment_filename if self.attachment_filename is not None else self.source_filename
        return filename

    def is_public(self):
        return self.access_type == FileAccessType.public

    def file_data_exists(self):
        return self.file_data and self.file_data.grid_id is not None

    def get_mimetype(self):
        return mimetypes.guess_type(self.source_filename)[0]

    def __str__(self):
        return "%s" % (self.title or self.slug)


# Regsister delete rule here becaue in User, we haven't imported FileAsset so won't work from there
FileAsset.register_delete_rule(User, "images", NULLIFY)
FileAsset.register_delete_rule(Group, "images", NULLIFY)


FileAsset.owner.filter_options = reference_options("owner", User)
# Use same way to format filesize as jinja by calling that filter directly
FileAsset.length.filter_options = numerical_options(
    "length",
    spans=[100000, 1000000, 10000000],
    labels=[
        _("Less than %(val)s", val=do_filesizeformat(100000)),
        _("Less than %(val)s", val=do_filesizeformat(1000000)),
        _("Less than %(val)s", val=do_filesizeformat(10000000)),
        _("More than %(val)s", val=do_filesizeformat(10000000)),
    ],
)
FileAsset.tags.filter_options = distinct_options("tags", FileAsset)
FileAsset.access_type.filter_options = choice_options("access_type", FileAsset.access_type.choices)

MimeTypes = Choices({"image/jpeg": "JPEG", "image/png": "PNG", "image/gif": "GIF"})
IMAGE_FILE_ENDING = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif"}


class ImageAsset(Document):
    slug = StringField(primary_key=True, min_length=5, max_length=60, verbose_name=_("Slug"))
    meta = {"indexes": ["slug"]}
    image = ImageField(thumbnail_size=(300, 300, False), required=True)
    source_image_url = URLField()
    source_page_url = URLField()
    tags = ListField(StringField(max_length=60))
    mime_type = StringField(choices=MimeTypes.to_tuples(), required=True)
    creator = ReferenceField(User, reverse_delete_rule=NULLIFY, verbose_name=_("Creator"))
    created_date = DateTimeField(default=datetime.utcnow, verbose_name=_("Created date"))
    title = StringField(min_length=1, max_length=60, verbose_name=_("Title"))
    description = StringField(max_length=500, verbose_name=_("Description"))

    def __str__(self):
        return self.slug

    # Executes before saving
    def clean(self):
        if self.title:
            parts = secure_filename(self.title).rsplit(".", 1)
            slug = parts[0]
        else:
            slug = self.id
        if not slug:
            raise ValueError("Cannot make slug from either title %s or id %s" % (self.title, self.id))
        new_end = IMAGE_FILE_ENDING[self.mime_type]
        new_slug = slug + "." + new_end
        existing = len(ImageAsset.objects(Q(slug__endswith="__" + new_slug) or Q(slug=new_slug)))
        if existing:
            new_slug = "%i__%s.%s" % (existing + 1, slug, new_end)
        self.slug = new_slug
