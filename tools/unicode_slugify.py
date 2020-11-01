# -*- coding: utf-8
import re
import unicodedata
from text_unidecode import unidecode


def _sanitize(text, ok):
    rv = []
    for c in text:
        cat = unicodedata.category(c)[0]
        if cat in "LN" or c in ok:
            rv.append(c)
        elif cat == "Z":  # space
            rv.append(" ")
    return "".join(rv).strip()


# Extra characters outside of unicode alphanumerics that we'll allow.
SLUG_OK = "-_~:."


def capitalize(s):
    m = re.search(r"[\W\d]+", s)
    end = m.end() if m else 0
    rv = s[0:end] + s[end : end + 1].upper() + s[end + 1 :]
    return rv


def slugify(s, ok=SLUG_OK, lower=True, spaces=False, only_ascii=False, space_replacement="_"):
    """
    Creates a unicode slug for given string with several options.
    L and N signify letter/number.
    http://www.unicode.org/reports/tr44/tr44-4.html#GC_Values_Table
    :param s: Your unicode string.
    :param ok: Extra characters outside of alphanumerics to be allowed.
               Default is '-_~'
    :param lower: Lower the output string.
                  Default is True
    :param spaces: True allows spaces, False replaces a space with the "space_replacement" param
    :param only_ascii: True to replace non-ASCII unicode characters with
                       their ASCII representations.
    :param space_replacement: Char used to replace spaces if "spaces" is False.
                              Default is dash ("_") or first char in ok if dash not allowed
    :type s: String
    :type ok: String
    :type lower: Bool
    :type spaces: Bool
    :type only_ascii: Bool
    :type space_replacement: String
    :return: Slugified unicode string
    """

    if only_ascii and ok != SLUG_OK and hasattr(ok, "decode"):
        try:
            ok.decode("ascii")
        except UnicodeEncodeError:
            raise ValueError(
                ('You can not use "only_ascii=True" with ' 'a non ascii available chars in "ok" ("%s" given)') % ok
            )

    new = _sanitize(unicodedata.normalize("NFKC", str(s)), ok)
    if only_ascii:
        new = _sanitize(unidecode(new), ok)
    if not spaces:
        if space_replacement and space_replacement not in ok:
            space_replacement = ok[0] if ok else ""
        new = re.sub(r"[%s\s]+" % space_replacement, space_replacement, new)
    if lower:
        new = new.lower()

    return new
