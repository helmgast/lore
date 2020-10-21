from ctypes import ArgumentError
import pathlib
import frontmatter
import re
from lore.model.shop import parse_datetime
from lore.model.topic import (
    LORE_BASE,
    Association,
    Name,
    Occurrence,
    Topic,
    TopicFactory,
    create_basic_topics,
    PATH_OK,
)
from tools.unicode_slugify import capitalize, slugify


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

# TODO import from sheets
# Col named "Name" or "Names" is the Topic Name. Each cell value is split by " / " or "\n" to create a list of names.
# For other cols, if it ends with an @ it's an assocation, if it ends with an "!" it's an occurrence.

# Col named "Kind" or "Type" is the Topic Kind.

# For Association cols, lookup the col header (except the @) as a Role. Fetch other Role and Instance based on that (how?). 
# Each cell is assumed to be a name of the T2 topic of the association.

# For Occurrence cols, lookup the col header (except the !) as a Kind. Each cell is assumed to be URI if it matches a URI regex, otherwise content. (what happens if cell is HYPERLINK?)

# Scopes are either added to the column (applying to all) or to the cell (applying to that instance) or in separate column named with a prefix "Scopes "?

# default_bases and default_scopes and default_associations can be added via the import command.

# TODO Any prefix to URLs produced or keep as relative
# TODO How to handle alias topics
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
    topic_default_scopes = factory.default_scopes.copy()
    if "author" in data:
        a = factory.make_topic(names=f"{data['author']}@")
        topic_default_scopes.append(a.pk)

    if "title" in data and data["title"]:
        # Always insert at beginning as this is primary name
        # TODO We capitalize to avoid ugly mixed case, but in theory a topic may intentionally be lowercase
        t.add_name(name=capitalize(str(data["title"])), scopes=topic_default_scopes, index=0)
    created_at = None
    if "created_at" in data and not job.batch.context.get("ignore_dates", False):
        # Remove tzinfo because all other dates in Lore, even if they are UTC, have tzinfo=None (offset-naive)
        created_at = parse_datetime(data["created_at"]).replace(tzinfo=None)
        t.created_at = created_at
    source = None
    if github_wiki := job.context.get("github_wiki", ""):
        github_id = re.sub(r'[\/\\:*?"<>|]', "", data["id"])
        github_id = re.sub(r"\s+", "-", data["id"])
        if github_id:
            source = github_wiki + github_id

    # Manage inline links
    # ^  [^\]]+\]: ([^ ]+) - finds all reference style links at end, run value through uslugify and then basify to try and find the right topic, link with full domain.
    def reflink_repl(match):
        if match:
            if (title := match.group(1)) and (link := match.group(2)):
                return f"{title}https://{factory.basify(slugify(link, PATH_OK))}"
            else:
                job.warn(f"Reference link {match.group(0)} of {data['id']} is malformed")
                return match.group(0)
        else:
            raise ArgumentError("No match object send to replacer")

    data.content = re.sub(r"^(  [^\]]+\]: )([^ ]+)$", reflink_repl, data.content, flags=re.MULTILINE)

    t.add_occurrence(content=data.content, uri=source, kind=f"{LORE_BASE}article", scopes=topic_default_scopes)

    if "map" in data:
        t.add_occurrence(uri=data["map"], kind=f"{LORE_BASE}map_point", scopes=topic_default_scopes)

    if "kind" in data:
        t.kind = factory.make_topic(data["kind"], created_at=created_at)

    # Remove languages for rest of scopes, as it won't really make sense on associations
    scopes_without_lang = [s for s in topic_default_scopes if s not in ("lore.pub/t/sv", "lore.pub/t/en")]

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
                    scopes=scopes_without_lang,
                )

        if "occurrence" in links and type(links["occurrence"]) is list:
            for occurrence in links["occurrence"]:
                t.add_occurrence(uri=occurrence, kind=f"{LORE_BASE}image", scopes=scopes_without_lang)

        if "mention" in links and type(links["mention"]) is list:
            for mention in links["mention"]:
                mention = capitalize(str(mention))
                # If necessary, make a category from name, including the right scopes
                t.add_association(
                    t2=factory.make_topic(names=(mention, topic_default_scopes), created_at=created_at),
                    kind=f"{LORE_BASE}link",
                    r1=f"{LORE_BASE}source",
                    r2=f"{LORE_BASE}target",
                    scopes=scopes_without_lang,
                )

        if "category" in links and type(links["category"]) is list:
            for category in links["category"]:
                category = capitalize(str(category))
                # If necessary, make a category from name, including the right scopes
                t.add_association(
                    t2=factory.make_topic(names=(category, topic_default_scopes), created_at=created_at),
                    kind=f"{LORE_BASE}categorization",
                    r1=f"{LORE_BASE}sample",
                    r2=f"{LORE_BASE}category",
                    scopes=scopes_without_lang,
                )
    return t
