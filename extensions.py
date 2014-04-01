from flask.ext.mongoengine import MongoEngine
db = MongoEngine()

from flask.ext.babel import Babel
babel = Babel()

#i18n
# @babel.localeselector
# def get_locale():
#   return "sv"  # request.accept_languages.best_match(LANGUAGES.keys()) # Add 'sv' here instead to force swedish translation.

from flask_wtf.csrf import CsrfProtect
csrf = CsrfProtect()

from flaskext.markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import ImagePattern, IMAGE_LINK_RE
from markdown.util import etree

class NewImagePattern(ImagePattern):
  def handleMatch(self, m):
    el = super(NewImagePattern, self).handleMatch(m)
    alt = el.get('alt')
    src = el.get('src')
    parts = alt.rsplit('|',1)
    el.set('alt',parts[0])
    if len(parts)==2:
      el.set('class', parts[1])
      if parts[1] in ['gallery', 'thumb']:
        el.set('src', src.replace('/asset/','/asset/thumbs/'))
    a_el = etree.Element('a')
    a_el.set('class', 'imagelink')
    a_el.append(el)
    a_el.set('href', src)
    return a_el

class AutolinkedImage(Extension):
  def extendMarkdown(self, md, md_globals):
    # Insert instance of 'mypattern' before 'references' pattern
    md.inlinePatterns["image_link"] = NewImagePattern(IMAGE_LINK_RE, md)
