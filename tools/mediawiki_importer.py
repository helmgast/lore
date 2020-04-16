import os
import re
from xml.etree import ElementTree as ET
import json
import io
import panflute as pf
from tools.batch import JobSuccess
import pprint

from pymongo import uri_parser
from tools.unicode_slugify import slugify

# PATTERNS

# Mediawiki legal characters:
#  $wgLegalTitleChars = %!\"$&'()*,\\-.\\/0-9:;=?@A-Z\\\\^_`a-z~\\x80-\\xFF+
#  Filenames have to be valid titles as above but also has additional illegal characters:
#  $wgIllegalFileChars = :\\/\\\\ . Illegal characters are replaced with -

clean_linebreaks = re.compile(r'\\*\n+', re.MULTILINE)
SLUG_OK = '-_~.:'

unescape = re.compile(r'\\([^\`*_{}\[\]\(\)>#+-.!])')  # Replace with group

# This matches links ![text](uri title) and similar. Uses negative look-behind to NOT match
# escaped \[ \] \( \).
link_matcher = re.compile(
    r'!?(?<!\\)\[([^\]]*)(?<!\\)\](?<!\\)\((.*?)( .*?)?(?<!\\)\)', flags=re.DOTALL)
category_pattern = re.compile(r'category|kategori', flags=re.IGNORECASE)
occurrence_pattern = re.compile(r'media|fil|file|image', flags=re.IGNORECASE)
redirect_pattern = re.compile(
    r'^#(REDIRECT|OMDIRIGERING)', flags=re.IGNORECASE)
# link_text_invalid_chars = re.compile(r'[#<>[\]\|{}`\\]+')
#link_text_invalid_chars = re.compile("[^%!\"$&'()*,\\-.\\/0-9:;=?@A-Z\\\\^_`a-z~\\x80-\\xFF+]")
#uri_invalid_chars = re.compile("[]")

ignore_ns = ("Special|Talk|Diskussion|User|Användare|User_talk|Användardiskussion|File_talk|Fildiskussion|"
             "MediaWiki|MediaWiki_talk|MediaWiki-diskussion|Template|Mall|Template_talk|Malldiskussion|Help|"
             "Hjälp|Help_talk|Hjälpdiskussion|Category_talk|Kategoridiskussion|Bilddiskussion")
simplify_image_links = re.compile(
    r'\[\[(File|Image|Fil|Bild)', flags=re.IGNORECASE)
occurrence_ns = "Media|File|Image|Fil|Bild"
category_ns = "Category|Kategori"
# Note that links may look like [](Category:_A_Thing) and should be [](A_Thing) after dropping NS
# (?!/): means match : if not before a /, as in http://
ns_divider = "[_\\s]*:(?!/)[_\\s]*"

all_ns_pattern = re.compile(
    f"[: ]?((?P<ns>{ignore_ns}|{occurrence_ns}|{category_ns}){ns_divider})?(?P<rest>.*)", flags=re.DOTALL | re.IGNORECASE)
ignore_ns_pattern = re.compile(
    f"[: ]?({ignore_ns})", flags=re.DOTALL | re.IGNORECASE)
occurrence_ns_pattern = re.compile(
    f"[: ]?({occurrence_ns}){ns_divider}", flags=re.DOTALL | re.IGNORECASE)
category_ns_pattern = re.compile(
    f"[: ]?({category_ns}){ns_divider}", flags=re.DOTALL | re.IGNORECASE)


def wikitext_generator(wiki_xml_file):
    tree = ET.parse(wiki_xml_file)
    root = tree.getroot()
    ns = "{http://www.mediawiki.org/xml/export-0.3/}"
    for page in root.findall(f".//{ns}page"):
        text = page.find(f".//{ns}text").text or ""
        # Fix, spaces in wikitable attributes breaks pandoc
        text = text.replace(' = "', '="')
        text = text.replace(
            " '''", "'''")  # Fix, space before ending ''' (bold) breaks
        # Pandoc doesn't recognize localized or incorrectly cased namespaces as image links, e.g.
        # [[Fil: [[image: [[file: will become just a normal link.
        text = simplify_image_links.sub(r"[[Image", text)
        yield {
            "title": page.find(f"{ns}title").text or "",
            "created_at": page.find(f".//{ns}timestamp").text or "",
            "text": text
        }


def action_count_headers(elem, doc, job):
    if isinstance(elem, pf.Header):
        doc.headers[elem.level] = 0


def action_arrange_headers(elem, doc, job):
    if isinstance(elem, pf.Header):
        if elem.level in doc.headers:
            elem.level = doc.headers[elem.level]
        if elem.content and isinstance(elem.content[0], pf.Strong):
            strong_contents = elem.content[0].content
            del elem.content[0]
            for i in range(len(strong_contents)-1, -1, -1):
                elem.content.insert(0, strong_contents[i])


def action_clean_link(elem, doc, job):
    if isinstance(elem, pf.Link):
        if elem.title == "wikilink":
            elem.title = ""
        if len(elem.content) == 0:
            s = elem.title or elem.url
            elem.content = [pf.Str(s)]
    elif isinstance(elem, pf.Image):
        if elem.title.startswith("fig:"):
            elem.title = elem.title[4:]
        elem.attributes.clear()
    elif isinstance(elem, pf.LineBreak):
        if elem.index == 0:  # No need for a LineBreak at beginning of a paragraph
            job.warn("Removed hard line break at start of paragraph")
            return[]


def action_extract_namespace(elem, doc, job):
    if isinstance(elem, pf.Link) or isinstance(elem, pf.Image):
        url_match = all_ns_pattern.match(elem.url)
        # assert text_match is not None, f"all_ns_pattern ({all_ns_pattern.pattern}) didn't match '{matchobj.group(1)}'"
        assert url_match is not None, f"all_ns_pattern ({all_ns_pattern.pattern}) didn't match '{elem.url}'"
        assert url_match.group(
            'rest') is not None, f"all_ns_pattern ({all_ns_pattern.pattern}) didn't get rest group '{elem.url}'"
        elem.url = url_match.group('rest').strip()
        assert elem.url
        ns = url_match.group('ns')
        if doc.is_redirect:
            doc.links.setdefault('alias_for', set()).add(slugify(elem.url))
            return []  # Remove the link
        elif isinstance(elem, pf.Image):
            doc.links.setdefault('occurrence', set()).add(elem.url)
            return elem
        elif ns:
            # leading : in namespace means not intended as category in wikilinks
            if category_pattern.match(ns):
                doc.links.setdefault('category', set()).add(elem.url.replace('_',' '))
                return []  # Category links remove themselves
            elif ignore_ns_pattern.match(ns):
                return pf.Strikeout(*elem.content)
            else:
                job.warn(
                    f"Forcing unknown namespace {ns} from {url_match.group(0)} to be a mention")
        # Don't count regular URLs as mentions
        if not elem.url.startswith("http"):
            doc.links.setdefault('mention', set()).add(elem.url.replace('_',' '))
            elem.url = slugify(elem.url)


def action_print_links(elem, doc, job):
    if isinstance(elem, pf.Link) or isinstance(elem, pf.Image):
        job.debug(elem)


def clean_headers(h):
    offset = 0
    if 1 in h:
        h[1] = 2
        offset += 1
    for i in range(2, 7):
        if i in h:
            h[i] = min(i+offset, 6)
        else:
            offset -= 1
    return h


def job_wikitext_to_markdown(job, data):
    title, text = data['title'], data['text']
    all_pages = job.context['all_pages']
    id = slugify(title)
    job.id = id
    file_path = os.path.join(job.context['out_folder'], id+".md")
    # job.info(f"Writing {title} to {file_path}")

    assert len(title) > 0, "Title cannot be empty"
    match = all_ns_pattern.match(title)
    if match and match.group('ns') and not job.is_bugreport:
        job.warn("Skipping page as title includes a Mediawiki namespace")
        job.success = JobSuccess.SKIP
        return

    is_redirect = redirect_pattern.match(text)

    if id in all_pages and not job.is_bugreport:
        if not is_redirect and not all_pages[id][1]:
            job.warn(
                f"Skipping page '{title}' as it has same id ({id}) as '{all_pages[id][0]}' and none are redirects")
            job.success = JobSuccess.SKIP
            return
        elif is_redirect:
            # Current page is just a redirect to something with same slugified id, so we can ignore it
            job.success = JobSuccess.SKIP
            return
    else:
        all_pages[id] = (title, is_redirect)
    if job.context.get('filter', None) and job.context['filter'] not in id and not job.is_bugreport:
        #print(f"filter={job.context['filter']}, id={id}, in it={job.context['filter'] in id}")
        job.success = JobSuccess.SKIP
        return

    doc = pf.convert_text(text, input_format="mediawiki", standalone=True)
    doc.links = {}
    doc.is_redirect = is_redirect
    doc.headers = {}
    if not job.is_bugreport:
        pf.run_filters([action_count_headers], doc=doc, job=job)
        clean_headers(doc.headers)
        job.debug(f"Headers: {doc.headers}")
        pf.run_filters([action_arrange_headers, action_clean_link,
                        action_extract_namespace, action_print_links], doc=doc, job=job)
    if not job.batch.no_metadata:
        # Use RawInline to avoid using markdown escape rules on the content
        doc.metadata['id'] = pf.RawInline(id)
        doc.metadata['title'] = pf.RawInline(title)
        doc.metadata['created_at'] = data['created_at']
        # Sort all metadata and wrap every item in RawInline to avoid markdown escaping
        doc.metadata['links'] = {key: list(map(lambda x: pf.RawInline(x), sorted(subset))) for (key, subset) in doc.links.items()}
    output_format = 'markdown-header_attributes-simple_tables-link_attributes-inline_code_attributes-implicit_figures-raw_attribute-smart'
    # extra_args = ["--wrap=none"]
    extra_args = ["--columns=100"]

    mdtext = pf.convert_text(doc, input_format="panflute", output_format=output_format, standalone=True, extra_args=extra_args)
    if "<!-- -->" in mdtext:
        job.warn("Empty HTML comment found")

    # Pandocs YAML writer assumes content is markdown, which means it will escape things like underscores. See issue https://github.com/jgm/pandoc/issues/2139
    # mdtext = frontmatter.dumps(postdata) + "\n" + mdtext
    json_str = ""
    if job.is_debug:
        with io.StringIO() as fs:
            pf.dump(doc, fs)
            json_str = json.dumps(json.loads(fs.getvalue()), indent=2)
    if not job.is_dry_run:
        with open(file_path, 'w') as f:
            f.write(mdtext)
            if json_str:
                f.write("\n\n```json\n")
                f.write(json_str)
                f.write("\n```")
            job.info(f"Written to file {file_path}")
    elif job.is_bugreport:
        print("BUGREPORT:\n------------")
        print(f"pandoc -f mediawiki -t {output_format} {' '.join(extra_args)} <<EOF\n{text}\nEOF")
        print(json_str)
        print("------------")
        return

    # THINGS TO FIX/WARN
    # We can identify a number of common issues and either warn for them or fix them. Warn is the default
    # either because an auto-fix can be too invasive, or because we haven't created a fix. Here are some of those:

    # PAGE LEVEL
    # __TOC__ and __NOTOC__ (or any __x__ magic word https://www.mediawiki.org/wiki/Help:Magic_words)
    # {{Kampanj/D6K}} e.g. templates. Requires more work, would be a later feature.
    # replace \<linebreak> with two linebreaks to separate paragraph (in most cases)
    # remove unnecessary escapes e.g. \" (but note that \- is needed if at start of line)
    # remove (empty) HTML comments
    # Warn for HTML tags as they may be unintentional (e.g. <i> would be unnecessary, or <tbd> is not a tag)
    # remove \'\'\'
    # remove emtpy list items like '-   '
    # remove unnecessary empty lines (last)
    # remove/convert remaining wiki-formatting such as '' and '''
    # formatting without space after, e.g. **Definition**text continues
    # Lower header levels without higher, e.g. only lvl 3s
    # Bolded words on their own row, should be headers
    # Single word on own line with empty line before and after - intended as header
    # Bolded beginning of paragraph that isn't followed by a :
    # Remove double space
    # Merge sequential lines marked as code with `...`
    # Paragraph ending with \ instead of empty line to separate to next para
    # Accidental dash in beginning of line, making a list but intended as "tankestreck"
    # _ for italics and ** for bold (not * or __)
    # Fix incorrect title characters: MediaWiki allows these [%!\"$&'()*,\-.\/0-9:;=?@A-Z\\^_`a-z~\x80-\xFF+], and disallows #<>[]|{}
    # Non-smart apostrophes etc
    #   Straight quotes ( " and ' ) into “curly” unicode
    #   Backticks-style quotes (``like this'') into “curly” unicode
    #   Dashes (“--” and “---”) into en- and em-dash entunicodeities
    #   Three consecutive dots (“...”) into an ellipsis unicode
