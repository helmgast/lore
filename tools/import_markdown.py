import pathlib
import frontmatter

from lore.model.shop import parse_datetime
from lore.model.topic import LORE_BASE, Association, Name, Occurrence, Topic, TopicFactory, create_basic_topics


def doc_generator(markdown_files_path, match):
    p = pathlib.Path(markdown_files_path)
    for file in p.glob("**/*.md"):
        doc = frontmatter.load(file)
        if "id" not in doc.keys():
            doc["id"] = file.stem
        if not match or match in doc["id"]:
            yield doc


def make_url(url_part, job):
    return url_part


# TODO Any prefix to URLs produced or keep as relative
# TODO How to detect author for imported data from frontmatter
# TODO Inline links are relative, do we need to make the absolute or point to root?
# TODO Whether to upload files from an upload dir
# TODO What the full path should be for files
# TODO Summarize stats
def job_import_topic(job, data):
    factory: TopicFactory = job.context["topic_factory"]

    # TODO we need to resolve alias in a more complete way, merging topics. Save for later.
    # alias_for = data.get('links', {}).get('alias_for', [''])[0]
    # if alias_for and data.get('title'):
    #     t = factory.make_topic(alias_for)
    #     t.add_name(name=data['title'], scopes=[default_lang])
    #     return  # We are done with the alias markdown as it's just a name for another topic
    t = factory.make_topic(id=data["id"])
    if "title" in data and data["title"]:
        # Always insert at beginning as this is primary name
        t.add_name(name=data["title"], scopes=factory.default_scopes, index=0)
    created_at = None
    if "created_at" in data and not job.batch.context.get("ignore_dates", False):
        # Remove tzinfo because all other dates in Lore, even if they are UTC, have tzinfo=None (offset-naive)
        created_at = parse_datetime(data["created_at"]).replace(tzinfo=None)
        t.created_at = created_at
    t.add_occurrence(content=data.content, kind=f"{LORE_BASE}article", scopes=factory.default_scopes)

    if "links" in data:
        links = data["links"]
        if "alias_for" in links and type(links["alias_for"]) is list:
            for alias in links["alias_for"]:
                # We use ID instead of title to look up, expecting that the alias topic is created from another MD document
                t2 = factory.make_topic(alias, created_at=created_at)
                if t2 == t:
                    print(f"{t2} ({alias}) and {t} ({data['id']}) recognized as same topic, do no more")
                else:
                    print(f"{t2} ({alias}) is an alias for {t} ({data['id']}), should merge in to latter")
                t.add_association(
                    t2=t2,
                    kind=f"{LORE_BASE}alternative_naming",
                    r1=f"{LORE_BASE}alias",
                    r2=f"{LORE_BASE}primary",
                    scopes=factory.default_scopes,
                )

        if "occurrence" in links and type(links["occurrence"]) is list:
            for occurrence in links["occurrence"]:
                t.add_occurrence(uri=occurrence, kind=f"{LORE_BASE}image", scopes=factory.default_scopes)

        if "mention" in links and type(links["mention"]) is list:
            for mention in links["mention"]:
                t.add_association(
                    t2=factory.make_topic(names=mention, created_at=created_at),
                    kind=f"{LORE_BASE}link",
                    r1=f"{LORE_BASE}source",
                    r2=f"{LORE_BASE}target",
                    scopes=factory.default_scopes,
                )

        if "category" in links and type(links["category"]) is list:
            for category in links["category"]:
                t.add_association(
                    t2=factory.make_topic(names=category, created_at=created_at),
                    kind=f"{LORE_BASE}categorization",
                    r1=f"{LORE_BASE}sample",
                    r2=f"{LORE_BASE}category",
                    scopes=factory.default_scopes,
                )
    return t
