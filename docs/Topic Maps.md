# Topic Maps

A Topic Map is a [standardized format](https://en.wikipedia.org/wiki/Topic_map#Current_standard) for describing concepts and their relations. Think of it as the index at the back of a book merged with a mind map.

Let's think about what an index is. It's not just a list of words that appeared somewhere in the book. It identifies important concepts that a book is about, and tries to map them to where more information exist about them (pages). Proper indices also often contain some relationship between these concepts, for example sub-topics or cross-references. Because indices are not just words, a human mind is required to attempt to map the ideas contained in the book to representative topics and their references within the text.

But if you remove the constraints of a typical book index and imagine that any topic can be related to any other topic, you start to get a mind map, or a graph. Additionally, you realize that information may not just reside in pages of a book, but actually use some form of universal location, such as a web site. Now you can create a map of topics and reference each topic to a set of information sources.

The real power in topic maps comes in associations, that is, how topics relate to each other. A Bus _is a_ Vehicle. Here both Bus and Vehicle are topics (that is, words that represent an idea or concept). But even the relation is a topic, that is link of _being something_. And in this two-way relation, the Bus can be seen as having the role of an _Instance_ and the Vehicle having he role of a _Category_. And in turn Vehicle can have an association with Machine, but in this association it's the Vehicle that is the Instance. So every relation between topics is described also by topics. To get further into Topic Maps, read these articles:

- [TAO of Topic Maps](https://ontopia.net/topicmaps/materials/tao.html)
- [A Practical Introduction to Topic Maps](http://techquila.com/tech/topic-maps-intro/)
- [Topic Maps on MSDN](https://docs.microsoft.com/en-us/previous-versions/aa480048(v=msdn.10))
- [Topic maps dead?](https://www.strehle.de/tim/weblog/archives/2015/06/14/1763)
- [Topic maps as file systems](http://www.garshol.priv.no/blog/200.html) _shows that topic maps can be understood as a file-system_

## Why so obscure?

Topic maps are a great theoretical construct but if you search around, you quickly realize they are pretty obscure. Very few references exist and the software and sources tend to be very dated. Almost the same fate seem to have happened to _semantic web_ [more here](http://www.garshol.priv.no/blog/261.html). For some reason organizing our knowledge and idea worlds does not attract a lot of interest. I think there are a few reasons:

1. Topic maps, semantic webs and similar all tend to come with a lot of abstraction and a lack of realistic examples of use.
2. It's very powerful to describe everything as a topic, even the relations with other topics, but it also makes it hard to get started. You might feel you need to create dozens of topics just to get the most basic of ideas represented properly. It can feel like trying to fill a swimming pool with a teaspoon.
3. Virtually all user interfaces in this space are old and poor. They use abstract terms, requires a lot of user input (e.g. limited auto-complete) and don't look sexy.
4. Ultimately, however useful these types of maps are in theory, in practice human knowledge and social graphs seems to be fairly well represented by tools we have today, like social networks, Google search and Wikipedia. Sure, they all use some graph databases or semantic technologies under the hood but in general, they more use brute force methods like text search (and lately, deep neural networks) that seem enough to get some value out of large amount of unstructured social and textual data. In other words, the topic maps have not yet proven their value.

## Other methods of semantic graphs or knowledge graphs

Topic maps plays in a fuzzy, messy area of research and standards where nothing really has become mainstream or de facto. In a broad sense, there are two competing concepts for representing graphs of knowledge: _topic maps_ and _resource description framework_ (RDF). Topic maps is a bit more complete, including scoping and bi-directional associations, whereas basic RDF is centered around subject-predicate-object, e.g. one-directional relationships. To read more about the differences and standards, [see here](http://www.garshol.priv.no/blog/92.html). In general, Topic Maps can be converted to RDFs and vice versa [see here](http://lingo.uib.no/trond/TopicMaps/Moore%20-%20RDF%20and%20Topic%20Maps%20An%20Exercise%20in%20Convergence.pdf)

## Why use topic maps for game worlds?

Lore is all about making it easy to create content for fictional worlds (games, books, movies, etc). Why are topic maps suitable for this?

1. When a game grows in content, it will invariably become harder to find and relate all concepts presented across many books. So a cross-book index is a great feature.
2. Apart from books, there will be PDF:s, magazine articles and external blogs referencing topics. It would be great to be able to add these so that the whole community can be part of it.
3. Building a large index is complex and time consuming. By making it easy for the community to participate, all can do their part to, for example, quickly add to the topic "Minas Tirith" a page in a book that mentions it, or a link to a blog that talks about it.
4. By having a machine-readable structure of all topics in a world, it becomes easy to assist in creation and generation of new content. For example, to easily find all cities in Gondor, all people in Minas Tirith, and so on.
5. The separation between topic space and occurrences is very suitable for published game worlds. There is a right or wrong (canon) in terms of what topics are part of the world, and you can decide to filter all references to occurrences based on whether it's official material, extended canon, community material, etc.
6. The scope concept of maps makes it easy to filter the world based on what you need, and for things such as separating rules, in-world content and meta-content (content about the world or it's writers).
7. If we build a system for topic maps, we can separate the actual content management to a more traditional CMS API with articles (as long as the topic can be seamlessly integrated into the frontend itself).
8. Scopes can be used to keep track of a mix of canon and community provided material as mentioned in 5), and also to filter the view of the world in different ways. A great use of scope is also to limit associations and references to time periods (if we can find a way to serialize the scope). For example, association between Sweden and King Wasa as ruler is only valid if we are in the time scope of 1521-1560.

## How to make them better

For me, topic maps offers a clean abstraction for creating worlds. When I write role-playing games, we authors do create topic maps. Some of them are just in our heads, and some of them in more crude formats such as long lists or tables. But with the right tool, we could encode all our ideas about the worlds we create in an efficient way. That would not only help our writing to be consistent and re-producible in different formats. It would also help users build more content and computers to generate new content. The last one's real interesting - when a computer can traverse a topic map, it may be able to generate an infinite amount of detail.

But to do this, topic maps need to get better. Here's what I'm thinking:

1. A clean API that offers read and write access to topics. GraphQL is possibly very well suited for this. It should be moddable and pluggable so that it's easy to add new functionality, not just new topics.
2. A rich vocabulary of basic topics that makes it easy to create most relations you might need in a fictional world. By having these building blocks ready the world can be built much faster.
3. Some way of importing an offline book index, or a list of concepts, to quickly get a start in terms of content.
4. Topic suggestion methods. One of the simplest is to look for words beginning with capital letters (as in good old Wikipedia). Make it a one click operation to create topics whenever a reader goes through a text.
5. A clean graph visualization. When graphs are shown on the web, they tend to use force-directed widgets that are fun to click around a bit but rarely offers real power to the user. In addition, they are often slow and not friendly to mobile. We need a lighter version of a graph, that both makes it easy to click around and to add new topics and relations with just a click.
6. Topic templates. Generic abstractions tend to kill creativity, whereas templates and constraints fuel them. Don't let the UI feel like a generic topic map, represent each topic type in a rich manner that both looks good, provides relevant info and makes it interesting to add just a few more details. For example, a Person should have a nice little portrait and easy ways of adding relatives. A Place should have a map location that links to a map widget.
7. Easy content linking. You should be able to throw any URL at the topic and it would link to it, but even better, it should recognize the content type and offer micro-interfaces to them. For example, Google Docs links, images stored across the web, Youtube videos, spinnable 3D-models and so on.
8. Fun ways of searching. Graph traversal has already been mentioned, but why not have a timeline view for temporal topics, a map for physical representation, organizational or ancestral trees for people. And these views should make it easy to add details, because this is where people's creativity is triggered.

## How to fill the map with content?

We could design a fantastic topic map system but it's useless without a critical mass of content. Sure, usability will help users to add material, but they tend to be put off by empty pages. These are ways we could start populating the topic map of a game world.

1. A completely empty topic map is not worth much, because new users are required to fill up a lot of very basic topics. To give some structure, there should be a set of UI preferred meta-topics. A meta-topic is a topic that doesn't reference content in the world itself, but things like something being a Place, a Person or having the association of instance_of, placed_in, etc. This becomes the starting vocabulary, if you want.
2. Quickly import lists of topics from Google sheets. The sheets are unlikely to have any relationships (associations) between topics, but they would have some description or metadata to be pulled in. For improved UX, make it possible to re-sync the content of these sheets with the topic map.
3. Import an existing book index (exact format to be determined).
4. Import a MediaWiki database. Apart from the article content itself, use the Wikilinks and the categorization to create the topic map.
5. Import Markdown with Front Matter (or direct from Wordpress?)
6. Read a text and identify all terms based on what is capitalized, removing common non-topic words and maybe using stem-matching (and maybe later some machine learning). Additionally, topics could be provided with a regex matcher-name, so that we can custom match some names in text. We can never get 100% coverage, but we can discover a lot of new Topics. Even better if we can automatically create occurrences based on where in the text we found them, but we need to convert the location within the imported text to a location in a website / PDF / book depending on the source, this can be tricky.

All importing needs to be made safe to re-import, so that we can "throw" many sources at the topic map and be sure not to destroy data. This implies that we can identify topics solely by their name, e.g. a unique slug created from the name. 

# Implementing Topic Maps

## Data Model of a Topic Map

See `lore/model/topic.py`.

## Pre-loaded topics

It's important to pre-load some topics with Lore, as the interface will expect some of them to exist (but not break if not!). They all come under the `lore.pub/meta/` namespace, below we just refer to the slug part.

### Associations
``` 
/* Uses LTM format, that is: [ topic-slug : topic_type = "Name" =]

located-in 
subtype-of
appears-in
born-in
died-in
killed-by
part-of

[located-in : hierarchical-relation-type = "Located in"
                                         = "Contains" / container
    @"http://psi.ontopedia.net/located_in"]
[subtype-of : hierarchical-relation-type = "Subtype of"
                                         = "Supertype of" / supertype
    @"http://www.topicmaps.org/xtm/1.0/core.xtm#superclass-subclass"]

/* -- TT: (untyped) -- */
[appears-in = "Appears in"
            = "Dramatis personae" / work
    @"http://psi.ontopedia.net/appears_in"]
[based-on = "Based on"
          = "Source of" / source
    @"http://psi.ontopedia.net/based_on"]
[born-in = "Born in"
         = "Birthplace of" / place
    @"http://psi.ontopedia.net/born_in"]
[completed-by = "Completed by"
              = "Completed" / composer
    @"http://psi.ontopedia.net/completed_by"]
[composed-by = "Composed by"
             = "Composed" / composer
    @"http://psi.ontopedia.net/composed_by"]
[Creator = "Creator"
         = "Skaper" / norwegian
    @"http://purl.org/dc/elements/1.1/creator"]
[died-in = "Died in"
         = "Died here" / place
    @"http://psi.ontopedia.net/died_in"]
[exponent-of = "Exponent of"
             = "Represented by" / style
    @"http://psi.ontopedia.net/exponent_of"]
[has-voice = "Has voice type"
    @"http://psi.ontopedia.net/has_voice"]
[killed-by = "Killed by"
           = "Kills (by)" / cause-of-death perpetrator
    @"http://psi.ontopedia.net/killed_by"]
[Language = "Language"
    @"http://purl.org/dc/elements/1.1/language"]
[libretto-by = "Libretto by"
             = "Wrote libretto for" / librettist
    @"http://psi.ontopedia.net/libretto_by"]
[part-of = "Contains"
         = "Part of" / part
    @"http://psi.ontopedia.net/part_of"]
[premiere = "First performed at"
          = "Hosted première of" / place
    @"http://psi.ontopedia.net/premiere"]
[published-by = "Published by"
              = "Publisher of" / publisher
    @"http://psi.ontopedia.net/published_by"]
[Publisher = "Publisher"
           = "Utgiver" / norwegian
    @"http://purl.org/dc/elements/1.1/publisher"]
[pupil-of = "Teacher/pupil"
          = "Pupil of" / pupil
          = "Teacher of" / teacher
    @"http://psi.ontopedia.net/pupil_of"]
   {pupil-of, descr, [[A relationship between a pupil and his teacher. The Italian Opera Topic Map only includes teachers of composition.]]}
[revision-of = "Revision of"
             = "Revised as" / source
    @"http://psi.ontopedia.net/revision_of"]
[Subject = "Subject(s)"
         = "Tema(er)" / norwegian
         = "Tema for" / norwegian value
         = "Subject of" / value
    @"http://purl.org/dc/elements/1.1/subject"]
[sung-by = "Sung by"
         = "Sings" / person
    @"http://psi.ontopedia.net/sung_by"]
[takes-place-during = "Takes place during"
                    = "Setting for" / event
    @"http://psi.ontopedia.net/takes_place_during"]
[takes-place-in = "Takes place in"
                = "Setting for" / place
    @"http://psi.ontopedia.net/takes_place_in"]
[unfinished = "Unfinished"
    @"http://psi.ontopedia.net/unfinished"]
[written-by = "Written by"
            = "Wrote" / writer
    @"http://psi.ontopedia.net/written_by"]
```

Example Topic maps:
- https://www.ontopia.net/omnigator/models/topicmap_complete.jsp?tm=ItalianOpera.ltm&pageView=master
- Schema.org can provide inspiration, and some of the occurrences can be tagged with it https://schema.org/docs/schemas.html

## URL and ID schemes for topic maps

An optimal ID/URI for a fictional world topic would be `:publisher/:world/:topic`.

This would not support homonyms, e.g. Gondor the King and Gondor the country, but to keep it simple, that can be solved by the naming of the topic itself (thereby changing the id). It's also fully possible to create a topic representing the homonym itself, and then link to other topics that it refers to.

While pre-established Lore meta-topics (e.g. Person, etc) could be identified by `lore.pub/meta/:topic`. This may not actually be an URL that serves any content (but it could also list all associated topics). Note that the lore.pub domain is shared across all publishers, e.g. they share the same meta-topics (they come with the Lore software). That doesn't exclude the possibility of `:publisher:/meta/:topic`.

Although the ID is an URI, it may not match to an actual page to serve. That is up to a CMS that uses the Lore API.

Canoncial topic descriptions won't be the only type of content a publisher produces. They might produce blog posts, perhaps at an URL like `:publisher/blog/:some_post_slug` or `:publisher/:world:/blog/:some_post_slug`, and these would be referenced as any other occurrence (just not considered canonical). It's also likely that a publisher want to write about their products at e.g. `:publisher/products/eon` or they might create an online book. It doesn't really matter, except to avoid collisions.

## Authorization and roles in topic maps

Like a wiki, we want as many people as possible to have the possibility to add to our world (topic map). But we also need to control access to avoid spamming and destroying data (especially as we probably won't have a revisions system on the topics). Additionally, it's great if we can handle if that there is not one unified source of truth about a fictional world. Some content is considered canonical, other is community. 

In Lore's Topic model, we don't track creators or editors of individual topics, they are all considered a common resource. After all, the Topic itself has almost no data. The valuable data lies in Occurrences (and less so in other characteristics). And each characteristic can have ownership as it will be scoped by the publishing user. Additionally, external occurrences of course have ownership that lies outside of Lore.

While reading any data on Lore is public, editing requires a logged in user. Any user is given one or more claims in a format like `role|publisher.com/world`. An action is permitted IF the role permits the action, AND the claim path is a prefix to either the ID of the topic OR the ID of a scope that exists on the characteristic being edited. A characteristic is a Name, an Occurrence or an Association.

### Contributor

A contributor is a user that is allowed to add content but not change or delete. Additionally, contributor content gets a special scope that requires editor action to approve before it becomes part of the general content.

- Can add a characteristic, scoped with `contributed-content`, if the claim matches the topic ID
- Can propose edit to a characterstic, by duplicating the characteristic and setting scope as `contributed-content`
- Can create a new topic, if the ID it would get matches the claim
- Later feature: Can propose words to be marked as topics in the text. Tricky as it would require some addressing of words in the text or ability to change the text.

In addition to contributed scope, we would also add the user-id to the scope. Users by default see their own scope, regardless, while other’s won’t see any community-proposed unless they explicitly add it to the filter. Also, users have editing rights to their own ID, which means they can edit characteristics they've added. When showing contributed edits, if they match another occurrence/association in the topic (using some heuristic), we would show them as overriding the previous in some way, e.g. a simple diff, or showing them next to each other in red and green.

### Editor

- Can edit any characteristic, including an approval action for `contributed-content` (which just means to change the scope to `community-content` or `canon`).

### Owner

- Same as editor, but can also delete topics.

## Multiple publishers and worlds

When a publisher digitizes their world, a first step is to create as many topics as possible that represents topics in the world, which obviously then are considered canon. The topics might be bare (not many characteristics), but that's something the community can help with adding.

Eventually, we will get the case that contributors want to add new topics, such as their own created character or place, to a world controlled by another publisher.

The first step is to associate the topic to a world created by original publisher, e.g. associate to topic Eon (`helmgast.se/eon`) with an association that is scoped as `contributed-content`. This would mean it shows up in listings of topics under Helmgast's Eon page, but not marked as canon. The downside is that the Eon topic might become extremely large. If we use the path component `eon` we don't need to create an association, but we have to assume that `eon` path is unique among all publishers.

By default, new topics are created under the contributor's own domain at a selected path, e.g. `mypub.lore.pub/eon/x`. This means if a user visits X, they might leave the Helmgast domain and enter the Mypub domain.

It's also possible to propose a topic to belong to another publisher, e.g. give it the id `helmgast.se/eon/x`. That means giving up any control as the topic id domain determines access rights as well as accessible URL, domain, theming, etc. You could do this by a setting when creating the topic. All the characteristics would still be scoped as `contributed-content` and to the publishing user that created it (`user@mybpub.lore.pub`). We would default to not showing topics that only have contributed titles, as we would consider them unapproved, but once a user with access to Helmgast approves it, it can show up in listings.

### Questions

- [ ] Can contributors use their own URLs and ID schemes, e.g. random page at their site?
- [ ] What are the queries needed to perform listings considering above scheme? There are e.g. two ways to query topics in a world - all topics linked to "MyWorld" or all topics with an ID containing "myworld".
- [ ] Associating all articles to a specific world will make that world topic have an very large association list. MongoDB has a max size Document size of 16 MB (maybe implying 100k associations as limit). Solutions:
  a) Create one-directional associations specifically for worlds, but we need logic to know when to search the DB for inbound associations instead of just reading the association list.
  b) Create a faux association built from the path components, e.g. a topic is automatically "part of" any path component in it's ID. Problem is, those part components are not globally unique as they lack a domain, so `eon` would have to be unique globally, or we can't assume `mypub.lore.pub/eon/x` is part of `helmgast.se/eon/` (which is hard to argue logically anyway)
  c) Create a collection of associations, so each association is a document. This however creates extra fetching (one query with many documents)
  d) Force publishers giving away control of their topics to link it to another world.
- Language is full of disambiguities. One such kind is aliases, where multiple names are associated with the same topic. The easy way to handle alias would simply be to create a new topic for each alias and link them using associations. Problem is that associations and textual links between topics gets fragmented: some might point to an alias and some to the original. It would be easy to lose info, or you'd need to graph search all aliases at display time. A better approach is to merge them, listing each alternative name as scope alias in the names list. You could even leave the text links untouched if you could search alternative names when resolving a link. It gets a bit more tricky however when we have multiple publishers. 

## Combining topic maps with existing CMS

A lesson I've learnt is the risk of building large monoliths where everything gets entangled. It's also hard to build one system that does it all within limited time. So the hypothesis is to implement topic maps as a layer on top of (any) content management system.

Take a normal Wordpress / Netlify or similar setup. You can create articles, publish them, get suitable URL schemes and so forth. What they lack is the total flexibility of topic maps. But let's add that on top:

Each page gets a client loaded component (can also be pre-rendered) that will fetch the page as a topic. So when we visit the content page "Minas Tirith", we use the presumed canonical URL to fetch the matching Topic object, with it's list of Names, Occurrences and Associations. This can be rendered to the user as "Also known as", "Resources" and "Relations", for example. Some Relations, and maybe the Topic type, can be given special focus on the page to denote things like the page's Category (in this case, a Place). If the user is authenticated to the topic API, we can also let the component modify the Topic data, such as adding a URL to his personal blog page, upload an image and so forth. You could also imagine the Topic component to offer an overlaid search or browsing experience.

In this way, we need minimal change of the CMS itself, while the user will see the topics still as closely integrated with the content. It degrades gracefully in that the content page would work perfectly fine without a loaded topic component. If the CMS is statically generated, it also makes sense that you can edit the topics in real-time even when the content might need to go through some push/pull/generate type process.

However, there are of course some challenges to making this happen:

1. For the best user experience, the topic API must be authenticated against using the same credentials as the CMS, and this might still need some "internal wiring"
2. Some data need to go from the CMS page to the topic API. At least the URI, but possibly also some metadata like the page title and author, at least at first "link-up" time. And what happens if these things are edited in the CMS, how to sync up with the topic API?
3. To integrate well into the CMS frontend, we need to have multiple "mount points" or access to some template. Although not required, it's much better if the Topic component can share the same framework (e.g. React)
4. To avoid confusion, we might need to de-activate some of the categorization systems of the CMS, such as tags, categories, etc, as they would double up with Topic maps and confuse people.
5. Most CMS come with a separate editing interface (admin) vs the public facing page, and for best UX, we also need to embed the Topic component in this interface.

This integration is primarily assumed to happen where the same publisher controls the Topic Map and the CMS. But it's possible the Topic Map could be seen as a 3rd party integration on top of other CMS:s, but that would have to be a later consideration.

## Occurrence types

Without topic maps, visiting `helmgast.se/eon/drunok` should just be a plain old blog type page or post. But with the topic map data added on top, as mentioned, we'd add some data on top. For the occurrences in particular, we'd probably want to present them in different ways depending on the type of URL. This functionality is very suitable for a pluggable architecture, where the community over time can create _adapters_ that convert a URL into some presentation format (and also that renders some form that creates an URL according to some format). In the data model, each occurrence has a `type`, which of course is another Topic, but a hard-coded one. Based on this Type and the URL, we could pick from a list of provided adapters to render it. The fallback would of course be to render each occurrence as a simple `<a>`-link. But you could imagine adapters like:

### Link

Can be displayed as a simple A, a preview fetch link (if supported) or a QR code.

### PreviewLink

### QR

### Bibliographic reference

A bibliographic reference, in a simplified format, including Title, Year, Author, URL, Publisher and Pagerange. See bibliographic formatting styles: https://www.scribbr.com/citing-sources/citation-styles/

### PDF

A PDF URL with an added page reference that is supported in some browsers. Displays as a PDF thumbnail.

### Image

An image URL. Can optionally be a Cloudinary (or similar) URL with added parameters for conversion, format, etc. Or can use a format keyword that has a pre-configured setting. Additionally has a role parameter, e.g. whether it's a wide (Hero), thumbnail or similar, so that we can find this occurrence easily when listing topics in different ways.

### 3D-model

USDZ files can be displayed directly in Apple devices.

### OEmbed

Some parameters to identify and display. Can include Youtube videos, Spotify, etc. Problem with having them all with the same type is that we miss the semantic meaning. An alternative is to have OccurrenceType as e.g. spotify-playlist and our editor knows that such type is displayed as OEmbed.

### Map:Point

A point x,y in a basic 2D coordinate system, with a URL to where the map is served. Assumes the URL serves a tiled map that takes x,y parameters, possibly additional parameter liked bounding box. We need to create a simple map server that can create a tiled map of any image.

### Map:GeoPoint

A WGS84 coordinate system point (lat, long), with a URL to where the map is served.

### Map:Polygon

A polygon in a basic 2D coordinate system (e.g a list of x,y:s that form a polygon), with a URL to where the map is served.

### Map:Geopolygon

A WGS84 coordinate system polygon (e.g a list of lat, longs that form a polygon), with a URL to where the map is served. Can be Google Map or similar service that supports WGS84.

### Previous

A special reference to a URL that shows "previous" content, e.g. previous chapter. Can be rendered as a left arrow.

### Next

A special reference to a URL that shows "next" content, e.g. next chapter. Can be rendered as a right arrow.

### <Metadata type> (start, stop, DoB, DoD, 

We can also have a number of metadata types associated with the meta-topics like Place (is that a co-ordinate or we store it in a Map reference?), Person (Date of Birth, Date of Deat), Event (start, stop), etc. These are not links but contain the data directly.


To make life easy for users, we could automatically suggest a type for an URL that has been given based on URL-pattern matching.
```
# Occurrence types from Italian Opera Topic Map sample
article
audio 
bibliographic reference
date-of-birth
date-of-death
description
gallery
illustration
video
website
```


## OccurrenceAdapters

- Schema of the adapter's fields (list of labels and field types)
- Serialization function from fields to URL string
- Deserialization function from URL to fields (also works as validation function?)
- Display component
- Optional edit component (could be auto-generated into a basic form from the schema)
- Optional metadata about how to store adapter data in the database, e.g. geo-coordinates that are not in the URL


## Lists and queries

- Query based on field sorting (name, dates?)
- Query based on graph associations, e.g. X steps away with type Y
- Query based on map, query by bounding box. The tricky part is that we can have many map backgrounds, so there is no global query, unless we find a way to overlay various images on top of a global coordinates.
- Query based on timeline. Need some way of representing the in-world time axis and calendar (?). Tricky part here is if the event data (e.g. start and stop time) are considered an occurrence on some timeline-page, or some special characteristic on the Topic object.

For the queries to be efficient, we may need to add extra indexed (denormalized) fields either on Topic or on a separate collection, e.g. to do geoqueries.

We often want to filter characteristics of a Topic through scope, for example to translate. We provide a list of ids and request to filter characteristics by them. It means, return any characteristic with a scope that matches either one of the provided, or all of the provided. 

We could also set an association pointing to a wildcard ID. This means it resolves to a query, not an individual topic.


## Open questions

[x] Custom IDs in MongoDB 
[ ] Unique IDs for Topics (slugs) and their relation to Name
[ ] Shorthand function for creating topics and associations
[ ] Handling of thumbnails and icons for topics
[x] Metadata we want to store on each topic. created_at, updated_at, owner?
[ ] How to use scopes. In the standard, they are considered a limitation, and lack of scope means no limitation. But we might want to have scopes also as a way of tagging or filtering topics, not just limiting. E.g. you might add a scope "MartinAuthored" just to be able to note who edited what. Basic idea is to use it for both depending on context.


## Personal knowledge management

There is an active trend for building personal knowledge systems that is very similar to Topic Maps. It's usually represented as a folder of interlinked Markdown, or as an app with a cloud database behind. Lore Topic Maps are intended to be shared, not personal, but apart from that, there are many similarities. So we should consider:
- Ability to import common formats of linked markdown from these apps
- Maybe ability to have a Markdown folder backend to represent the topic map
- Look through these apps for good concepts on usability for large knowledge graphs

## Import sources

### Mundanapedia
Import from Mediawiki-source to Markdown repo.
`flask wikitext-to-markdown ~/dev/src/encyclopedia-mundana/eon_dump.xml ~/dev/src/encyclopedia-mundana/`
Considered canon, no named author, published by Helmgast, in Swedish.
`flask import-markdown-topics ~/dev/src/encyclopedia-mundana -b lore.pub/t -b helmgast.se/eon -s sv -s canon -a existence( this:concept, helmgast.se/eon:world) --github-wiki https://github.com/helmgast/encyclopedia-mundana/wiki/`

### Drängopedia
Import from Mediawiki-source to Markdown repo.
Considered community content, authored by Ola or other author, published by Drängopedia, in Swedish.
`flask import-markdown-topics ~/dev/src/drangopedia -b lore.pub/t -b helmgast.se/eon -b drangopedia.lore.pub/eon -s sv -s community -a existence( this:concept, helmgast.se/eon:world) --github-wiki https://github.com/helmgast/drangopedia/wiki/`

### Neotech terms
Import from Sheets.
Considered canon, authorless, published by Helmgast, in Swedish or English (depending).

### Neotech eqip list
Import from Sheets.
Considered canon, authorless, published by Helmgast, in Swedish.

### PRD Zones
Import from Sheets, plus add map-functionality.
Considered canon, authorless, published by Helmgast, in Swedish or English (depending).

### Kartor från kartpaket
Already imported online, but without any visual assets. Needs the shortlink to connect to topics to not break existing QR-kodes!
Considered canon, authorless, published by Helmgast, in Swedish.

### Neotech chargen
Already imported (not as topics), but need new data sheet and checking on it.

### Kampanj
Import from Wordpress archive to Markdown repo.
Considered community, authored by Martin et al, published by Kampanj, in Swedish.

### Nogo
Import from Joomla archive to Markdown repo.
Considered community, auhtored by Martin et al, published by Nogo, in Swedish.

### Noir
Import from Joomla archive to Markdown repo.
Considered community, auhtored by various, published by Helmgast, in Swedish.


## World hierarchy (old)

An idea of a structure is to use three characters to denote the role of the article in a tree. The keys could also be used as shortcuts to create a link within a text.

    @ link to
    & embed
    # revision
    World:Mundana
        &Text:...  (always a leaf node)
        &Media:... (also always a leaf node)
        @Place:Consaber
            @Place:Nantien
                @Person:Tiamel
                @Place:Nant
                    #rev67
                    #rev66
                    ...
        Event:Calniafestivalen
        Scenario:Calniatrubbel
            &Text:...
            @Scene:1
                @/mundana/consaber/nantien
                @/mundana/
            @Scene:2
            @Scene:3
        Character:Taldar

    Semantical structure
    World:Mundana
        Place:Consaber mundana/consaber
            Place:Nantien mundana/consaber/nantien
                Person:Tiamel mundana/consaber/nantien/tiamel
                Place:Nant mundana/consaber/
        Event:Calniafestivalen
        Scenario:Calniatrubbel
            Scene:1
                @/mundana/consaber/nantien
                @/mundana/
            Scene:2
            Scene:3
        Character:Taldar
