On slugs
============

Most content management systems have to deal with *slugs*, e.g. a name for a resource that is both human-friendly and machine-friendly, typically used for a canonical identifier in URLs or file names. A slug is derived from a human-friendly title, that often can include any available Unicode character. The conversion typically includes two steps:

1. A removal of characters that would cause problems or are unsupported for the environment where they are to be used. That can be characters with special meanings in URLs or file systems.
2. A normalization where we want to be able to compare or search for a version of a title that is always the same, typically this means lowercase (implying that "Content Title" and "Content title" will be identified as the same resource). It can also normalize different characters of whitespace into one or no whitespace. Essentially, a slug should never be the same for two resources that are considered different.

Traditionally, slugs were made with the whitelist approach - e.g. only allow certain characters, like ASCII. This is the safe method, and goes for supporting the lowest common denominator. But these days we have Unicode support in virtually all modern systems and that means a wealth of characters to uses. As my preferred approach is to make slugs as close representation to the title as possible, supporting as many languages and expressions as possible, I'd rather go for a black list approach. That is, which characters should we avoid, not which should we allow.

Additionally, in [Lore](https://lore.pub) we have the need to have a hierarchy represented in our slugs. Essentially, a slug should be unique across the whole system. The most typical way to represent hierarchy in strings is using paths, separated by `/`. This means that a slug is essentually a unique resource indicator, or a [URI](https://danielmiessler.com/study/difference-between-uri-url).

So what black lists of characters do we have to adhere to?

## URLs

There is a lot of differing information on what URL:s can include, and a number of RFC standard documents to define it. But in general, the characters that aren't allowed can still be included if URL Encoded. The problem with URL encoding is that URLs tend to get very ugly and not human-friendly. The good thing is that modern browsers automatically encodes and decodes, so that users rarely need to see the raw form.

## Markdown

In Markdown, link destinations, e.g. URL:s, can appear inline and in a reference section at the end. In principle, any character is allowed in the URL from Markdown's point of view, but a few characters can be interpreted as part of the Markdown syntax, so that we must avoid. As per [CommonMark specification](https://spec.commonmark.org/current/#link-destination) that means

- No `<` at beginning
- No ASCII space or control characters (they are parsed as an end of the URL and beginning of title section)
- Only espaced or balanced pairs of parentheses `()`

## Database identifiers

We use the slugs as native identifiers in MongoDB. But while MongoDB has some rules on what we can [name the fields](https://docs.mongodb.com/manual/reference/limits/#Restrictions-on-Field-Names) there are no rules on the content of the identifiers, as they are seen as any string value.

If we would convert to Firebase, and use a slug as a key, we can't use:

- `.$[]#/`

But it's not given that we would use an identifier in that way. The value of a property can be anything, like in MongoDB.

## File names

According to Mediawiki, [illegal characters for files](https://www.mediawiki.org/wiki/Manual:$wgIllegalFileChars) in addition to what's allowed in titles, are:

- `: / \`. Would be replaced with `-`.

We also want to stay compatible with Github Wiki, which supports using files in a repository. Those file names have the following limitations:

- `\ / : * ? " < > |`

## Mediawiki

Although Mediawiki is not a limiting factor for Lore, they have given serious thought to what characters can or can't be in content titles. Note that when Mediawiki talks about a title, it's both what you write into documents AND the slug used in a URL. That is something Lore is aspiring too as well. Their list of illegal characters are:
https://www.mediawiki.org/wiki/Manual:$wgLegalTitleChars

- `#<>[]|{}`, non-printable characters 0 through 31, and 'delete' character 127
- In addition, user-names are by default not allowed to use `@` as that is used to denote interwiki users (similar to Lore)

## Lore special characters

When we slugify a title in Lore, we also need to consider if we have given special meaning to any characters when we handle and parse ID:s. And we do; we both use them to denote hierarchy, authorization and identifying users. That means the characters can appear in a complete slug, but it cannot be generated in the conversion from the Title as it would be given a meaning that's not intende. The characters are:

- `/` as a path separator
- `@` as a username identifier
- `|` and line-break are additionally used to separate inline lists when we import data. Therefore it's safest not to allow them.

## Normalization and lowercasing

There has been a lot of back and forth in thinking about whether we need normalization or not, e.g. lowercasing. Almost all URL:s are lowercase, even though they don't have to be (Mediawiki is a big exception). But even system that allow any-cased URL:s often normalize under the hood, e.g. the "TiTle" and "title" URL:s lead to the same place.

We could store slugs in mixed-case, but if we still want to search for them normalized (e.g. "TiTle" and "title" is the same), we'd need to do a lowercased or case-insensitive comparison at every point in the app, such as importing data, comparing ID:s or querying the database. This is bug-prone and reduces performance. So we ruled that wouldn't be practical. Then the question is if we should do any normalization at all? But it would likely be unexpected for users that "Title" and "title" are two completely different articles, and any mistake in typing titles would generate a separate article.

So, while normalizing ID:s does remove nice capitalized Titles in URL:s, it was the most sane choice to make. What we can do, however, is to redirect mixed case URL:s in the  event that someone typed them in like that, and redirect to the correct case.