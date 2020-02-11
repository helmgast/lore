# Topic Maps

A Topic Map is a [standardized format](https://en.wikipedia.org/wiki/Topic_map#Current_standard) for describing concepts and their relations. Think of it as the index at the back of a book merged with a mind map.

Let's think about what an index is. It's not just a list of words that appeared somewhere in the book. It identifies important concepts that a book is about, and tries to map them to where more information exist about them (pages). Proper indices also often contain some relationship between these concepts, for example sub-topics or cross-references. Because indices are not just words, a human mind is required to attempt to map the ideas contained in the book to representative topics and their references within the text.

But if you remove the constraints of a typical book index and imagine that any topic can be related to any other topic, you start to get a mind map, or a graph. Additionally, you realize that information may not just reside in pages of a book, but actually use some form of universal location, such as a web site. Now you can create a map of topics and reference each topic to a set of information sources.

The real power in topic maps comes in associations, that is, how topics relate to each other. A Bus _is a_ Vehicle. Here both Bus and Vehicle are topics (that is, words that represent an idea or concept). But even the relation is a topic, that is link of _being something_. And in this two-way relation, the Bus can be seen as having the role of an _Instance_ and the Vehicle having he role of a ?_Category_. And in turn Vehicle can have an association with Machine, but in this assoication it's the Vehicle that is the Instance. So every relation between topics is described also by topics. Interested, [read more here](https://ontopia.net/topicmaps/materials/tao.html).

## Why so obscure?

Topic maps are a great theoretical construct but if you search around, you quickly realize they are pretty obscure. Very few references exist and the software and sources tend to be very dated. Similar to semantic web, for some reason organizing our knowledge and idea worlds does not attract a lot of interest. I think there are a few reasons:

1. Topic maps, semantic webs and similar all tend to come with a lot of abstraction and a lack of realistic examples of use.
2. It's very powerful to describe everything as a topic, even the relations with other topics, but it also makes it hard to get started. You might feel you need to create dozens of topics just to get the most basic of ideas represented properly. It can feel like trying to fill a swimming pool with a teaspoon.
3. Virtuall all user interfaces in this space are old and poor. They use abstract terms, requires a lot of user input (e.g. limited auto-complete) and don't look sexy.
4. Ultimately, however useful these types of maps are in theory, in practice human knowledge and social graphs seems to be fairly well represented by tools we have today like social networks to Google search and Wikipedia. Sure, they all use some parts under the hood but in general, they more use brute force methods like text search (and lately, deep neural networks) that seem enough to get some value out of large amount of unstructured social and textual data. E.g. the maps have not proven their value.

## Why use topic maps for game worlds?

Lore is all about making it easy to create content for fictional worlds (games, books, movies, etc). Why are topic maps suitable for this?

1. When a game grows in content, it will invariably become harder to find and relate all concepts presented across many books. So a cross-book index is a great feature.
2. Apart from books, there will be PDF:s, magazine articles and external blogs referencing topics. It would be great to be able to add these so that the whole community can be part of it.
3. Building a large index is complex and time consuming. By making it easy for the community to participate, all can do their part to, for example, quickly add to the topic "Minas Tirith" a page in a book that mentions it, or a link to a blog that talks about it.
4. By having a machine-readable structure of all topics in a world, it becomes easy to assist in creation and generation of new content. For example, to easily find all cities in Gondor, all people in Minas Tirith, and so on.
5. The separation between topic space and occurences is very suitable for published game worlds. There is a right or wrong (canon) in terms of what topics are part of the world, and you can decide to filter all references to occurences based on whether it's official material, extended canon, community material, etc.
6. The scope concept of maps makes it easy to filter the world based on what you need, and for things such as separating rules, in-world content and meta-content (content about the world or it's writers).
7. If we build a system for topic maps, we can separate the actual content management to a more traditional CMS API with articles (as long as the topic can be seamlessly integrated into the frontend itself).

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

## Steps to populate

We could design a fantastic topic map system but it's useless without a critical mass of content. Sure, usability will help users to add material, but they tend to be put off by empty pages. These are ways we could start populating the topic map of a game world.

1. A completely empty topic map not worth much, because new users are required to fill up a lot of very basic topics. To give some structure, there should be a set of UI preferred meta-topics. A meta-topic is a topic that doesn't reference content in the world itself, but things like something being a Place, a Person or having the association of instance_of, placed_in, etc. This becomes the starting vocabulary, if you want.
2. Quickly import lists of topics from Google sheets. The sheets are unlikely to have any relationships (associations) between topics, but they would have some description or metadata to be pulled in. For improved UX, make it possibly to re-sync the content of these sheets with the topic map.
3. Import an existing book index (exact format to be determined).
4. Import a MediaWiki database. Apart from the article content itself, use the Wikilinks and the categorization to create the topic map.
5. Import Markdown with Front Matter (or direct from Wordpress?)

# Implementing Topic Maps

## Data Model of a Topic Map

```
Topic
    Topic[] types # May be hardcoded to just one
    Name[] names # [0] considered canonical id
    Occurence[] occurences
    Association[] associations
    #! TopicDB also contains instance_of
    # Probably needs a description

Name
    String name
    Topic[] scopes
    #! TopicDB only has a single scope, and treats language as a special field
    #! standard includes variants of names

Occurence
    URI uri
    Topic type
    Topic[] scopes
    #! TopicDB also contains a resource field

Association
    Topic source
    Topic source_role
    Topic association_type
    Topic destination_role
    Topic destination
    Topic[] scopes
    #! TopicDB and standard groups source and source_role into a Member object first
```

## URL and ID schemes for topic maps

An optimal ID/URI for a fictional world topic would be `:publisher/:world/:topic`.

This would not support hononyms, e.g. Gondor the King and Gondor the country, but to keep it simple, that can be solved by the naming of the topic itself (thereby changing the slug).

While pre-established Lore meta-topics (e.g. Person, etc) could be identified by `lore.pub/meta/:topic`. This may not actually be an URL that serves any content (but it could also list all associated topics). Note that the lore.pub domain is shared across all publishers, e.g. they share the same meta-topics (they come with the Lore software). That doesn't exclude the possibility of `:publisher:/meta/:topic`.

Note that for topics, these URLs are only identifiers. The actual Topic object would be fetched from the GraphQL endpoint. When a user visits the URL of the topic `helmgast.se/eon/drunok`, we are instead fetching contents from a CMS, but the contents are considered the canonical description of the Topic `Drunok`. We just need to ensure this URL is as permanent as possible.

Canoncial topic descriptions won't be the only type of content a publisher produces. They might produce blog posts, perhaps at an URL like `:publisher/blog/:some_post_slug` or `:publisher/:world:/blog/:some_post_slug`, and these would be referenced as any other occurence (just not considered canonical). It's also likely that a publisher want to write about their products at e.g. `:publisher/products/eon` or they might create an online book. It doesn't really matter, except to avoid collisions.

## Authorization in topic maps

Like a wiki, we want as many people as possible to have the possibility to add to our world (topic map). But we also need to control access to avoid spamming and destroying data (especially as we probably won't have a revisions system on the topics). Additionally, if users can add content (e.g. occurences) it would be very useful to be able to separate what is canon (e.g. by the publisher) and what is not.

First, to avoid spamming, we require users to log in to edit any data (and as needed, we can use captchas or other throttles). By default, a user should be able to:

- Create new topics (but they would be marked by a scope that identifies the user, and a scope that identifies it as community content).
- Add names to existing topics, e.g. for translation or clarifications (again marked by scope as above).
- Add occurences on existing topics, that is, adding of content and links (again marked by scope as above)
- Add associations between existing topics (again marked by scope as above)

A user can be allowed to edit or delete links that have their scope, but it could be tricky as this could now be considered in use by others. This should probably be a setting.

## Combining topic maps with existing CMS

A lesson I've learnt is the risk of building large monoliths where every thing gets entangled. It's also hard to build one system that does it all within limited time. So the hypothesis is to implement topic maps as a layer on top of (any) content management system.

Take a normal Wordpress / Netlify or similar setup. You can create articles, publish them, get suitable URL schemes and so forth. What they lack is the total flexibility of topic maps. But let's add that on top:

Each page gets a client loaded component (can also be pre-rendered) that will fetch the page as a topic. So when we visit the content page "Minas Tirith", we use the presumed canonical URL to fetch the matching Topic object, with it's list of Names, Occurences and Associations. This can be rendered to the user as "Also known as", "Resources" and "Relations", for example. Some Relations, and maybe the Topic type, can be given special focus on the page to denote things like the page's Category (in this case, a Place). If the user is authenticated to the topic API, we can also let the component modify the Topic data, such as adding a URL to his personal blog page, upload an image and so forth. You could also imagine the Topic component to offer an overlaid search or browsing experience.

In this way, we need minimal change of the CMS itself, while the user will see the topics still as closely integrated with the content. It degrades gracefully in that the content page would work perfectly fine without a loaded topic component. If the CMS is statically generated, it also makes sense that you can edit the topics in real-time even when the content might need to go through some push/pull/generate type process.

However, there are of course some challenges to making this happen:

1. For the best user experience, the topic API must be authenticated against using the same credentials as the CMS, and this might still need some "internal wiring"
2. Some data need to go from the CMS page to the topic API. At least the URI, but possibly also some metadata like the page title and author, at least at first "link-up" time. And what happens if these things are edited in the CMS, how to sync up with the topic API?
3. To integrate well into the CMS frontend, we need to have multiple "mount points" or access to some template. Although not required, it's much better if the Topic component can share the same framework (e.g. React)
4. To avoid confusion, we might need to de-activate some of the categorization systems of the CMS, such as tags, categories, etc, as they would double up with Topic maps and confuse people.
5. Most CMS come with a separate editing interface (admin) vs the public facing page, and for best UX, we also need to embed the Topic component in this interface.

This integration is primarily assumed to happen where the same publisher controls the Topic Map and the CMS. But it's possible the Topic Map could be seen as a 3rd party integration on top of other CMS:s, but that would have to be a later consideration.

## Occurence types

Without topic maps, visiting `helmgast.se/eon/drunok` should just be a plain old blog type page or post. But with the topic map data added on top, as mentioned, we'd add some data on top. For the occurences in particular, we'd probably want to present them in different ways depending on the type of URL. This functionality is very suitable for a pluggable architecture, where the community over time can create _adapters_ that convert a URL into some presentation format (and also that renders some form that creates an URL according to some format). In the data model, each occurence has a `type`, which of course is another Topic, but a hard-coded one. Based on this Type and the URL, we could pick from a list of provided adapters to render it. The fallback would of course be to render each occurence as a simple `<a>`-link. But you could imagine adapters like:

- FetchLink: a normal URL fetcher a la Facebook that shows a preview
- Image: display as image
- 3D-model that can be seen directly on the page
- OEmbed (YouTube link etc)
- CloudinaryImage
- PDF (optional page reference)
- Book: a link to where to buy a piphysical book, plus a page reference or range displayed outside of the link.
- ArticleLink: reads the article content from our API and renders on the page. (this might possibly rather be a function of the CMS we use)

To make life easy for users, we could automatically suggest a type for an URL that has been given based on URL-pattern matching.

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
