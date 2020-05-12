import pathlib
import frontmatter
import datetime
import collections
from lore.model.topics import Association, Name, Occurrence, Topic
from tools.unicode_slugify import slugify


def doc_generator(markdown_files_path):
    p = pathlib.Path(markdown_files_path)
    for file in p.glob("**/*.md"):
        doc = frontmatter.load(file)
        if 'id' not in doc.keys():
            doc['id'] = file.stem
        yield doc


def make_url(url_part, job):
    return url_part



# # Central config
# Whether to dry-run
# Prefix (publisher, world) to id:s
# Any prefix to URLs produced or keep as relative
# Default language (not possible per page?)
# Default World, or way of mapping pages to World
# Whether to upload files from an upload dir
# What the full path should be for files
# Whether to user original dates or import dates as created time
# Scope to apply to imported data
# Update/upsert behavior for existing data in database
# Download list of topics (to keep in memory for checking)
# Iterate over files
# Add topics based on file and it's links. Note if topic exist as is (no DB update needed) or not.
# Add default topics
# Update links in text if necessary
# Summarize stats
def job_import_topic(job, data):
    # Expects data to always have property id
    # Will test for properties title, created_at, and links
    def get_topic(topic_id=None, title=None):
        if not topic_id and title:
            topic_id = slugify(title)
        if topic_id:
            topic = job.context['all_topics'].setdefault(topic_id, Topic(id=topic_id))
            if title:
                topic.add_name(name=title)
            return topic
        else:
            raise ValueError("Need either a topic_id or title")

    t = get_topic(data['id'])
    if 'title' in data and data['title']:
        t.names.append(Name(name=data['title']))
    if 'created_at' in data and job.batch.context.get('original_dates', True):
        t.created_at = datetime.datetime.strptime(data['created_at'], "%Y-%m-%dT%H:%M:%S%z").utcnow()  # ISO 8601
    if 'links' in data:
        links = data['links']
        if 'occurrence' in links and type(links['occurrence']) is list:
            for occurrence in links['occurrence']:
                t.add_occurrence(uri=occurrence, instance_of='image')

        if 'mention' in links and type(links['mention']) is list:
            for mention in links['mention']:
                t.add_association(get_topic(title=mention))

        if 'category' in links and type(links['category']) is list:
            for category in links['category']:
                t.add_association(get_topic(title=category), instance_of='categorizes-as', this_role="instance", other_role="category")

    # def commit():
    #     print(repr(t))
    # job.committer = commit
