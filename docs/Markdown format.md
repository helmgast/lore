Markdown format
===============

Markdown is a somewhat messy format, but it's still probably the best combination of human-readability and available tooling. So Lore very early on made the decision to have all text content stored as Markdown, not as HTML or custom JSON formats. There are some pros and cons of this of course:

### Pros
1. Easy to read and write for any type of user, you may not even need to know about the syntax.
2. Storing the text in database in a readable format makes debugging and exporting much easier.
3. Large ecosystem of tools
4. Compact data usage
5. Limiting the users expressibility (can't style everything, doesn't allow layouting) keeps things clean and simple.

### Cons
1. Do support the basic needs of Lore, we need some extensions (see below) and this makes tool support much more tricky.
2. Markdown is not directly machine readable and there are many tricky edge cases for going to and from the format.
3. The limitations of Markdown rules out some userexpressions or elaborate layout.

Standard and Extensions
----------

We use Github Flavoured Markdown, a superset of CommonMark. But we also need some extensions on top of that. They are:

1. Support for tables, including multi-line tables
2. Support for Frontmatter (at least at import, probably not in saved source)
3. Prefer Setext headings for H1 and H2 (more readable)
4. Support for shortcut reference links, e.g. [this] is a link.
5. Support for some styling of images (ut can be solved by appending to the URL!)
6. Support for strikeout
7. Supperscripts and subscripts (or may be solved by just unicode?)
8. Auto-identifiers (anchors) for headings
9. Embed non image-files using the same syntax (depends on URL). E.g. embed a Youtube video by ![](https://youtube.com/w=123).
10. Preferrably some support for comments, marks and spoilers
11. Raw HTML as escape hatch


Encoding and wrapping
----------

Original Markdown focused on plaintext representation written mostly in ASCII. But we have the full power of Unicode now, and therefore, it should be possible to store everything encoded in Unicode, avoiding ugly character codes and using e.g. smartypants style typographic details directly in the source. This also follows the goal of having the source content as true to original and as portable as possible (in the sense that no conversion is needed to export, not in the sense of supporting older systems).

Commonly, -- " and ' are converted to unicode variants when rendered. We'd rather convert them on user input, but store the finished version as unicode.

Another tricky part is whether we should hard-wrap lines in stored Markdown. The benefits is easy reading (on environments without a wrapper) and easy line-by-line diffing. On the other hand, it has to be re-wrapped at every edit, creating noise in changes. Our decision is to **not** wrap in source.

Markdown workflow
----------

Currently, the workflow goes as this

### Reading

1. Read markdown content from database
2. Render using Python Markdown to HTML on server
3. Serve to user

### Writing

1. Use WYSIWYG editor to edit content
2. Click save, export Markdown version of the edited HTML content
3. Store Markdown in database

or

1. Write raw markdown
2. Store Markdown in the database

We also have the messy case of switching between raw markdown and WYSIWYG on the editor. This means we have to also render Markdown -> HTML on clientside.

Editor requirements
----------

Finding the right editor is very hard. We have to strike a fine balance between meeting all our technical requirements, giving good UX and minimizing maintenance and own coding.

The optimal goal would be an editor that natively deals with Markdown, so that you can skip the error-prone step of converting between HTML and Markdown in the editor. Otherwise, it could also work if the editor uses a structured JS format that can be 1:1 converted to/from Markdown, e.g. an Abstract Syntax Tree.

1. It should support the extensions we want
2. It should allow editing and auto-completing hyperlinks (as we prefer reference shortcut links, we need to consider how the text is updated)
3. It should allow drag and drop of images. Image upload should be handled outside the editor itself however!
4. It shoud allow automatic saving to local storage.

### Editor ideas

- [TUI Editor](https://nhn.github.io/tui.editor). Supports GFM, has table support, WYSIWYG, etc. Looks a little off.
- 