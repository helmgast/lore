from lore.model.asset import get_google_urls
import re
from typing import Any, Dict, List
from urllib.parse import urlparse
from lore.model.shop import parse_datetime
from lore.model.topic import (
    LORE_BASE,
    Occurrence,
    TopicFactory,
    PATH_OK,
)
from tools.unicode_slugify import capitalize, slugify


def is_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def listify(obj, skip_falsy=True):
    rv = []
    if type(obj) is list:
        rv = obj
    elif obj is not None:
        rv = [obj]
    return [v for v in rv if v] if skip_falsy else rv


# TODO Any prefix to URLs produced or keep as relative
# TODO handle removal of characteristics, if they are empty (but how to find what to remove?)
# TODO How to handle alias topics
# TODO Inline links are relative, do we need to make the absolute or point to root?
# TODO Whether to upload files from an upload dir
# TODO What the full path should be for files
# TODO Summarize stats
def job_import_topic(job, data):
    factory: TopicFactory = job.context["topic_factory"]
    topic_default_scopes = set(factory.default_scopes)

    # TODO we need to resolve alias in a more complete way, merging topics. Save for later.
    # alias_for = data.get('links', {}).get('alias_for', [''])[0]
    # if alias_for and data.get('title'):
    #     t = factory.make_topic(alias_for)
    #     t.add_name(name=data['title'], scopes=[default_lang])
    #     return  # We are done with the alias markdown as it's just a name for another topic

    # Do first as will be added to default scopes
    if data.get("author", None):
        a = factory.make_topic(names=f"{data['author']}", is_user=True)
        topic_default_scopes.add(a.pk)

    t = None
    if id := data.get("id", None):
        t = factory.make_topic(id=data["id"])

    if "title" in data:
        for title in listify(data["title"]):
            if isinstance(title, str):
                name = str(title)
                scopes = []
            else:
                assert isinstance(title, dict)
                name = str(title["name"])
                scopes = [factory.basify(s) for s in listify(title["scopes"])]
            scopes.extend(topic_default_scopes)  # in-place
            if not t:  # first title makes our topic then
                t = factory.make_topic(names=(name, scopes))
            t.add_name(name=name, scopes=scopes)
    if not t:
        raise ValueError("Can't make topic, no id nor title in data")

    created_at = None
    if data.get("created_at", None) and not job.context.get("ignore_dates", False):
        # Remove tzinfo because all other dates in Lore, even if they are UTC, have tzinfo=None (offset-naive)
        created_at = parse_datetime(data["created_at"]).replace(tzinfo=None)
        t.created_at = created_at

    if data.get("kind", None):
        t.kind = factory.make_topic(names=data["kind"], created_at=created_at)

    # Manage inline links
    # ^  [^\]]+\]: ([^ ]+) - finds all reference style links at end, run value through uslugify and then basify to try and find the right topic, link with full domain.
    def reflink_repl(match):
        if match:
            if (title := match.group(1)) and (link := match.group(2)):
                basified = factory.basify(slugify(link, PATH_OK))
                if basified != link:
                    return f"{title}https://{basified}"
            job.warn(f"Reference link {match.group(0)} of {data['id']} is already absolute or malformed")
            return match.group(0)
        else:
            raise ValueError("No match object send to replacer")

    occurrences = data.get("occurrences", {})

    # Add the markdown content with special rule for getting github_wiki
    if hasattr(data, "content"):
        occ_args = {"content": data.content}
        if github_wiki := job.context.get("github_wiki", ""):
            github_id = re.sub(r'[\/\\:*?"<>|]', "", data["id"])
            github_id = re.sub(r"\s+", "-", data["id"])
            if github_id:
                occ_args["uri"] = github_wiki + github_id
        occurrences.setdefault("article", []).insert(0, occ_args)

    occurrence_key_mapping = {
        "reference": "bibref",
        "map": "map_point",
    }

    for key in sorted(occurrences.keys()):
        if occurrences[key]:
            if (id := occurrence_key_mapping.get(slugify(key), None)) :
                kind = factory.make_topic(id=id)
            else:
                kind = factory.make_topic(names=key)
            for occ in listify(occurrences[key]):
                kwargs = {"kind": kind.pk, "scopes": []}
                if isinstance(occ, str):
                    kwargs["content"] = occ
                else:
                    assert isinstance(occ, dict)
                    if "content" in occ:
                        kwargs["content"] = occ["content"]
                    if "uri" in occ:
                        kwargs["uri"] = occ["uri"]
                    if "scopes" in occ:
                        kwargs["scopes"] = [factory.basify(s) for s in listify(occ["scopes"])]

                # Detect if content is actually an URI
                if not kwargs.get("uri", None) and is_url(kwargs["content"]):
                    kwargs["uri"] = kwargs["content"]
                    del kwargs["content"]

                # Detect and normalize Google URL
                if google_uri := get_google_urls(kwargs.get("uri", "")):
                    kwargs["uri"] = google_uri["direct"]

                # Make internal links absolute
                if kind.pk == "lore.pub/t/article":
                    kwargs["content"] = re.sub(
                        r"^(  [^\]]+\]: )([^ ]+)$", reflink_repl, kwargs["content"], flags=re.MULTILINE
                    )

                kwargs["scopes"].extend(topic_default_scopes)
                t.add_occurrence(**kwargs)

    if map_url := data.get("map", None) or occurrences.get("map", None):
        t.add_occurrence(uri=map_url, kind=f"{LORE_BASE}map_point", scopes=topic_default_scopes)

    links = data.get("links", {})
    if "alias_for" in links:
        for alias in listify(links["alias_for"]):
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
                scopes=topic_default_scopes,
            )

    # TODO shouldn't be under links, change in mediawiki export
    if "occurrence" in links:
        for occurrence in listify(links["occurrence"]):
            t.add_occurrence(uri=occurrence, kind=f"{LORE_BASE}image", scopes=topic_default_scopes)

    link_key_mapping = {
        "mention": {"kind": f"{LORE_BASE}link", "r1": f"{LORE_BASE}source", "r2": f"{LORE_BASE}target"},
        "category": {"kind": f"{LORE_BASE}categorization", "r1": f"{LORE_BASE}sample", "r2": f"{LORE_BASE}category"},
        "part_of": {"kind": f"{LORE_BASE}inclusion", "r1": f"{LORE_BASE}part", "r2": f"{LORE_BASE}whole"},
        "correlation": {"kind": f"{LORE_BASE}correlation", "r1": f"{LORE_BASE}relation", "r2": f"{LORE_BASE}relation"},
        "ruler": {"kind": f"{LORE_BASE}rulership", "r1": f"{LORE_BASE}demesne", "r2": f"{LORE_BASE}ruler"},
    }

    for key in sorted(links.keys()):
        kwargs: Dict[str, Any] = link_key_mapping.get(slugify(key), None)
        if not kwargs:
            job.info(f"Skipping import data key {key}={links[key]} as not listed for import")
            continue
        else:
            kwargs = kwargs.copy()
        for ass in listify(links[key]):
            if isinstance(ass, str):
                kwargs["t2"] = ass
            else:
                assert isinstance(ass, dict)
                if "t2" in ass:
                    kwargs["t2"] = ass["t2"]
                if "scopes" in ass:
                    kwargs["scopes"] = [factory.basify(s) for s in listify(ass["scopes"])]
                # TODO check more characteristics
            kwargs.setdefault("scopes", []).extend(topic_default_scopes)
            kwargs["t2"] = factory.make_topic(names=(kwargs["t2"], kwargs["scopes"]), created_at=created_at)
            t.add_association(**kwargs)

    return t


topic_sheets_header = re.compile(r"^(?P<name>.*?)(?P<scope>\[[^]]+\])?\s*(?P<type>[#@&=])(?P<id>\w*)\s*$")
cell_lists_w_comma = re.compile(r"\s*[/|,\n]\s*")
cell_lists_wo_comma = re.compile(r"\s*[\n|]\s*")
leading_zero = re.compile(r"^0")
middle_zero = re.compile(r"–0")


def fix_bibrefs(bibrefs: List[str]):
    bf_map = {}
    for br in bibrefs:
        if br:
            parts = br.split(": ", 2)
            if len(parts) == 2:
                bf_map.setdefault(parts[0], []).append(parts[1].replace("–0", "–").replace(", 0", ", ").lstrip("0"))
    return [f"{b}: pp. {', '.join(p)}" for b, p in bf_map.items()]


def job_import_sheettopic(job, data, **kwargs):
    # Assumes sheet headers have format like 'Header name [default_scope1,ds2] &id' where scopes and id are optional.
    # At minimum, we use the &#@= chars to detect type of the column for creating a topic, e.g. how to translate the sheets
    # to topic typed input data.
    new_data = {}

    for k, datum in data.items():
        m = topic_sheets_header.match(k)
        if m:
            id = (m.group("id") or m.group("name")).strip()
            scopes = cell_lists_w_comma.split(m.group("scope")[1:-1]) if m.group("scope") else []
            datum = str(datum)
            if m.group("type") == "#":
                new_data["title"] = [{"name": v, "scopes": scopes} for v in cell_lists_wo_comma.split(datum) if v]
            elif m.group("type") == "=":
                new_data["kind"] = datum
            elif m.group("type") == "@":
                new_data.setdefault("links", {})
                values = [{"t2": v, "scopes": scopes} for v in cell_lists_wo_comma.split(datum) if v]
                new_data["links"].setdefault(id, []).extend(values)
            elif m.group("type") == "&":
                new_data.setdefault("occurrences", {})
                if id.lower() == "reference":
                    values = [{"content": v, "scopes": scopes} for v in fix_bibrefs(cell_lists_wo_comma.split(datum))]
                else:
                    values = [{"content": v, "scopes": scopes} for v in cell_lists_wo_comma.split(datum) if v]
                new_data["occurrences"].setdefault(id, []).extend(values)

    if "title" not in new_data or not new_data["title"]:
        raise ValueError("No title data means no id, this row can't be used")
    return job_import_topic(job, new_data)
