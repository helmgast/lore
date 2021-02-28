Scopes
=============

https://ontopia.net/topicmaps/materials/scope.htm
https://www.garshol.priv.no/download/text/a-theory-of-scope.pdf

Based on the Topic Map ISO standard, scope is *the extent of the validity of a topic characteristic assignment*. That mouthful basically means - when we say a topic's name "Ämne" is scoped in "Swedish" it means that this name is only valid if your *context* includes Swedish. What context is depends on circumstance, but it can simply be seen as a search parameter, a filter, a ranking, etc. So a topic can have many characteristics, but depending on the context, only some of those characteristics are considered valid (or relevant). Exactly how a context is compared with scope is not straightforward and we will come back to that. It should also be said that a characteristic can have no scope, and in the definition, that means it has the *unconstrained scope*. Basically, it just means it's valid in any context.

Swedish, and any scope, is just a reference to any other topic, but in most cases, you tend to use certain classes of topics as scopes, and they tend to be meta-topics, in the sense that instead of being part of the actual content, it describes the content. The literature mentions a number of common classes of scopes:

- **natural languages**, e.g. to scope in which language a name or occurrence is considered valid (and therefore relevant to a user)
- **classification systems**, e.g. "NO" as name is only valid as "ISO 3166 code"
- **name variations**, e.g. e.g. plural vs singular, sort name, or how an association topic like "Existence" can be described as "Exists in" or "Reified by" depending on the context (role).
- **access levels**, e.g. such as secret, spoiler, admin. The actual access control obviously has to be performed by the application. Can also include things like "only if purchased X", and the app controls who has what scope.
- **temporal validity**, e.g. this name or occurrence was only used during a specific time (where this time need to be defined as a Topic, not as a scalar, which can be a bit awkvard)
- **provenance or point of view**, the source of the characterstic. It can be very practical to see the topic map from the point of view of a source or creator. This can be as granular as individual creators or wider as a school of though or belief system (e.g. how the topic Jesus would be described differently by the jewish, christian and islamic belief systems)
- **audience**, e.g. this characteristic is only considered valid for a certain type of viewer, e.g. user vs admin or beginner vs advanced
- **source**, in terms of where the characteristic came from when importing, merging or mirroring data from outside
- **editorial status**, e.g. draft, deleted, archived, proposed, flagged, error

As scope can be any topic, there is of course the opportunity to see it as a general way of adding tags to characteristics, as long as it isn't better described as a characteristic in itself on the topic.

They natural way to classify the scope topics is using their type/kind characteristic, so that `sv`, `en`, `fr` all has kind `language`.

Finally, the area I'm interested to explore, is to see **revisions** as a scope. E.g., a characteristic can be given a scope that names the revision (or sets of revisions) that created this data. In this way, you would be able to use the scope to view the topic map as it has been created over time. But it's tricky considering the simplistic nature of scope just being an unstructured set of topics.

Context vs scope
-----------------

Scopes mostly play a role when we want to view the topics through some lens, which is a matter of applying a context. *In this context, show the characteristcs that are valid*. Note that topics don't have scopes themselves, they are always valid, but we could apply the context in two ways: a way to filter/render a list of topics, and a way to filter/render one topic (e.g. a list of characteristics). Context can be given through filter controls, user preferences and flags or simply the environment (e.g. what language the URL has and what map we are "in").

Question is, how can I compare a context (a set of topics) and a scope (also a set of topics) and produce a decision, e.g. to include or exclude in a filtered result. There is some debate around this in the sources and no clear consensus. Pepper describes the following cases when filtering:

1. Scope is a superset of Context
2. Scope is a subset of Context
3. Scope is identical to Context
4. Either Scope is a subset of Context or a superset of Context
5. Scope and Context have a non-empty intersection

1 is a basic AND search where we expect all of our Context to match, and 5 is a basic OR where any topic in Context (any search term, if you will) should match. This is where it gets tricky. For example we might want to prefer English and our context therefore includes `en`. If we follow method 1, we can't return anything without `en` in the scope, not even empty scopes. In reality, most characteristics will have empty scope to start with or are not language related (e.g. an image) and it would be unexpected to hide all of the just because the user prefers English. If we go for method 5, it works until the Context contains more things, for example `en` and `canon`. Here we would also get all characterstics scoped with [`fr` ,`canon`] which is also unexpected.

Pepper here draws the conclusion that we need to structure scope, and you'd quickly reach for a query language where you can compose AND, OR, and so forth together. And you might be able to do some of that thanks to the underlying database engine. But I'd like to try and come as far as I can without adding more required complexity.

One realization is that when you add `en` to your context, maybe you are actually saying remove all other languages from my context? If you had a filter control, you could easily see a checkbox for each available language, and a UI that deselects all other languages. In terms of set operations, that means we'd rather work with a negative context, a set of all things we don't want to see. And this makes some sense, because after all the data is there to be consumed, and perhaps its better to show by default than hide by default. So it gives us *method 6: Scope has an empty intersection with the negative Context*.

However, the negative context ought to be a hidden mechanism and not something to expose directly to the user. For example, it would be tiresome to have to manually deselect all languages you don't want, or when applying a temporal filter, to deselect all others. To make the UI work as a normal context, it imples what Pepper calls the *axes of scope*, e.g. sets of related scoping topics. So when you select `en` you actually add the difference of `[all_langs]` and `[en]` to the negative context. Without those axes or classes of scopes, you can't add anything to the negative scope. In practice, you may not always have the axis. It could be an *incidental* scope topic, e.g. one that falls outside the typical classes of scopes mentioned before. So the application may need to support two parameters for filtering: the positive and the negative context, e.g. the scope that a characteristic MUST and MUST NOT have.

Filtering on provenance
------------------------

When using topic maps to describe collaboratively produced worlds, you can filter your view in number of levels. The top level is to see everything. The level below is to filter on `canon`, `community` and `contrib`. The level below that is named worldviews. For example, a fictional world like Game of Thrones can have variations between the TV-series and the books, while both being considered official. There would be two `description` occurrences of the topic White Walker, one scoped to `got-books` and another to `got-tv` (as they describe White Walkers differently). A further level down, characteristics would be scoped with publisher. In this way, I could decide my context should include `canon` plus the publisher `got-fandom.com` because I trust them, but not others. And ultimately, I could filter on individual authors.

Whereas some of the scope axes can seem a bit superflous, provenance can be very powerful, as it solves a problem with many user generated worlds that not all content is created equal. Some will be considered better or more official than others. Worth noting is that Wikipedia doesn't really have this - it instead relies on editors to decide whats true or false but that also (intentionally) kills the creativity of people adding their own version of facts. But topic maps allow characteristics to exist in a continuum of true and false. *The truth is in the eye of the beholder.*

Displaying scopes
-----------------

As scopes is an optional metadata, and we can have many of them, we need to be careful not to clutter the view with a lot of scope data. It would also confuse casual users. So we need to find a minimal but still relevant display of scopes. We should use icons instead of text where possible.

When displaying a topic in the UI, we would try to *fold* similar characteristics together. For example, we can have a description box, with tabs for variant, titled by the scope difference. The difference is key here, we don't want to repeat what's common between the variants. If too many tabs, we put them in a dropdown menu, and you can press an expand button to fold them all out below eachother. The order of them would be based on best match to context plus some hard coded preferences like `canon` going before `community`.

There could be some value to show a message like "some scopes hidden" or "X scopes hidden" to remind users that they are not watching all the data available.

Scope and the identity of statements
------------------------------------

Characteristics in Topic Maps have no identities on their own, but equality can be done by comparing all their properties. [Garshol](https://www.garshol.priv.no/download/text/a-theory-of-scope.pdf) notes that scope is part of the equality, which means that two otherwise identical names but with different scope are considered different. 

You could however argue that if there are no differences in the data except the scope, you could keep just one copy of the data with a union of the two scopes. In an application, that would avoid creating unnecessary duplicate data by mistake. For Lore, *we should exclude scope from equality and merge the scopes with an existing characteristic if added*.

Adding scope
--------------

In an editing UI scope should probably be editable as a tag selector or based on similar controls when filtering on "axes of scope". But we should try and add automatic scope as well, to relieve the user of manual work. For example we can:

- Add `language` based on the selected UI language or analysis of the text
- Add `source` automatically based on where the data is entered
- Add `provenance` in terms of the user's identity, the user's publisher and whether the content is considered `canon` or `contrib` based on if the user belongs to the publisher of the world or not (`community` is contrib that's been approved).

Revision control
==================

To have full revision control of data is kind of a holy graal in data modelling. It's also notoriously tricky, a compromise of many goals. For our topic map based system, we need to explore different models of revision control. So what's the wish list?

1. To be able to view the edit history of a topic (with an assumption of also seeing provenance, e.g. who edited, when and why)
2. To be able to rollback to an earlier state (akin to git checkout)
3. To see differences between two edits and select the merger of the two (akin to git merge)
4. To be able to replace parts of an edit history (akin to git rebase)

Finally, there is a somewhat unique opportunity of revisions in topic maps that is similar to how software dependency management works. Say that we as a publisher has approved some contributed characteristic about our topic as `community`. That means it would show by default to most users (part of the default context). If a user edited that characteristic into something offensive, we wouldn't want to keep displaying that front and center. You could handle that by the application automatically removing the `community` stamp until approved again, but that means the old, approved version wouldn't be available in the mean-time.

A better approach would perhaps be to "pin" a version, and when there's an updated one, we could decide whether to include it or not. But is that important enough to motivate complete revision management through scope?

Usage patterns
--------------

Architectural decisions should obviously consider expected usage, and while we are mostly guessing at this point, it's anyway valuable. We expect the following in Lore:

- We will have mostly light editing activity, and mostly centered around adding new characteristics. Text content in occurrences may have more editing activity, but we will also try to use external sources (meaning, that version control could be solved externally). Removing data will be unusual. As a user edits via the UI we will know which specific occurrence is being edited.
  
- We are likely to do a lot of batch importing and re-importing by admins or power users. Due to the batch importing happening on a topic level from an unstructured source like markdown, it's hard to cleanly attribute each change of characteristics to existing characteristics.
  
- There is a clear value in having a history of edits on each topic, as multiple users can be active and the topics can be very long lived (akin to Wikipedia)
  
- Editing rights are given on topic level, permission levels of `read`, `add` and `edit`. `add` means you can contribute new characteristics (either from blank or by editing an existing) while `edit` means you can modify or remove anything.

Approaches
-----------

One is to do **save every version of the topic**. [It's very simple](https://www.mongodb.com/blog/post/building-with-patterns-the-document-versioning-pattern). But it doesn't support the mix and match requirement without a lot of extra wiring. You'd need to do a lot of diffing to find what's changed, and you'd end up storing a lot of duplicate data.

A second option is to do a **patch/diff of each topic**. It's more efficient than a full copy, and you can use [JSON patch](http://jsonpatch.com/) standard for storing and communicating the changes. As it's already a diff, it's pretty easy to show differences. But it still acts on the whole document, and may not support simple mix and matching of characteristics.

A third option is to **store revisions as a scope of each characteristic**, e.g. each name, association and occurrence. The tricky part here is that characteristics currently lack a unique identifier, so it's hard to track changes of one of the characteristics. It's somewhat akin to the lines in a text file when using git. You could keep a revision list under each individual characteristic, but that wouldn't work so well when the source of the update is external, such as YAML or text, where you can't represent the detailed structure. Same with having explicit identifiers, you'd need to auto-generate some hash or similar that wouldn't be natural or known to external sources, meaning an update from them wouldn't be easy to reconcile automatically. One weakness of revisions as a scope is that we can't revision control the scope edits themselves, same for scalars like `Topic.created_at`, `Topic.id` or `Topic.kind`.

Key use cases
-----------

### 1: Import and re-import

We first batch import 100 topics, call it change `A`. Then we add, edit and remove one occurrence on topic 1, let's call that change `B`. Then we want to re-import the 100 topics with corrections, `C`. How do we do that?

In Git there are two well known approaches to this. One is **merge**. In merge, we would consider `B` and `C` both children of `A`, and we would do a diff of them to identify non-conflicting and conflicting changes, and let the user resolve the conflicts. For example, both changes may have edited the name which is a conflict but `B` might have added a new occurrence which is not affected by `C`.

Another approach is to **rebase**. A rebase means that we either replace `A` with `C` and then apply `B` on top, or that we apply `B` on `A` and then `C` on `B`.

Note that as Git deals with unstructured data (text files) and doesn't store deltas, it has to do a diff between any pair of commits (changes). It's up to the diff algorithm on how efficient it is in automatically solving problems.

#### Implemented by scope

When we import `A` we give every characteristic the scope `A` in addition to what the import data includes. When we modify topic 1, we keep the `A` scoped characteristics as they are except adding the scope `archive`. The added and changed characteristic are both seen as new characteristics with scope `B`. The removed characteristic is implied by marking the old one as `archive`. If you browse topic 1, you would have a default negative context including `archive`, e.g. they would be hidden.

First import A
```
id: t1
names:
 - One [A]
 - Two [A]
 - Three [A]
 ```

Manual change B
(change Two to Deux, remove Three)
```
id: t1
names:
 - One [A]
 - Deux [B]
 - Two [A, archived]
 - Three [A, archived]
 ```

Import C replacing A
(Swedish using Ett instead of One)
```
id: t1
names:
 - Ett [C]
 - Deux [B]
 - Two [C, archived]
 - Three [C, archived]
 ```

 or

Import C adding to A
(Swedish using Ett instead of One)
```
id: t1
names:
 - One [A]
 - Deux [B]
 - Ett [C]
 - Two [A, archived]
 - Three [A, archived]
 ```

When we want to re-import `C`, we have to options: either replace `A` so that it never existed, or add `C` on top of `A`.
1) **Replace `A`**:
   1) For each topic, delete all characteristics with scope `A` (changes from `B` wouldn't be affected). Add every new characteristic with scope `C`.
2) **Rebase `A`**:
   1) As there can be any number of changes after `A`, we say that we add the `C` change on top of `A`. It basically implies we skip making any change in `C` that is already there with scope `A`. (we also ignore scope `archive`).

we could simply update all characteristics from `A` in-place. We'd need to replace the `A` scope and keep the `archive` scope if we wanted the import to exist before the `B` change (e.g. we rebase `B` on top of `C`). We could also keep the `A` change in `archive`, append all characteristics with scope `C`, and then run a diff algorithm to see how the edits of `B` apply on top of `C` (or we wouldn't know which of `C` changes to mark as archived).

When a change is made and added to the scope, we would also have created the change as a topic. That topic could include a description occurrence ("Commit message"), a created_at timestamp and an associations to previous (and later) change.

Note that if an import changes or adds topic IDs, there is no way to associate them with existing topics. Only way to do that, would be to also add an alias_for property on either of the topics.
### 2: Display edit history for topic

To see a history of edits on topic 1, you could find all change topics in it's scope and sort them by created date or their associations to eachother. You could display the commit message for each, and you could also somehow signify which characteristics were affected by each change. Note that one change can have impact on many other topic than the currently viewed. There is however not possible to show the typical "name was changed from A to B" or similar, because we don't have that granularity.

### 3: Remove a commit

You can remove the topic that represents the commit. You'd need to also remove all characteristics belonging to it, and you'd need to connect the previous with the later commit to keep the commit chain intact.

### 4: Using a pinned characteristic

This means that a user may want to only see the article text from a specific edit they (or someone else) did, instead of seeing the latest. A normal user would have a scope filter `NOT archived`, but a user with a pinned scope would use `NOT archived OR pinned-change`. However, this would mean the user has to see ALL changes associated with that change, so it might be a full import for example. Also, it wouldn't hide the latest change, they would be shown together. You also wouldn't be able to pin to a specific revision of a topic, as topics don't have revisions, just characteristics.

### Assorted notes

You could also try to find a natural diffing algorithm for each characteristic, but it's not given that's possible. It's attractive to look at scopes here, as they anyway take center stage in mixing and matching of characteristics, such as showing only edits from X or Y or in certain language.

Let's simplify and say a topic contains a list of tuples (data, scopes). Apart from adding and removing items, we can modify data of an item with same scope, modify scope with same data, or both at the same time. How can we tell if an item with (dataA', scopes) is an update to the previous dataA, or is a completely new item? Well:

Note that all characteristics are unique in a way. There is no need for two names with the same string, they are identical. There is no need for multiple associations of the same kinds between two same topics. And there is no need for multiple copies of the same data

We could create a scope for every revision made. If we know the latest such revision, we could use that to show the latest revision, or any previous. Problem is that for a complete document, we want to see the latest of each characteristic, which may be from different revisions, so it's not as simple as just showing characterstics with the latest revision scope.

We could treat the order of the characteristics as the way to induce revisions. Simply, later characteristics overwrites earlier ones, according to some logic. But what is that logic? If we have two names, the later overwrites the earlier if they don't have different scopes. First, it means that if we haven't scoped properly, e.g. two different languages, we would hide one of the languages with the other, which is not intuitive.

We could add a timestamp to all characteristics. Then we can sort them by time, but can still not tell two names apart. But we could have an archived scope, which we apply when an authorized user has decided that this characteristic is no longer relevant. This would work for most cases, except for text heavy occurrences. If it's edited back and forth, we would have two problems: lots of data duplicated, and they would all be listed in a long archive of almost identical texts. However, for texts, we could either use a diffing heuristic to display them as deltas, not copies. Or we would even store the data as a diff, not a delta (problem is then that the order is crucial to be able to re-create revisions in full).

Use case 1:



So let's see how far we can come by copying Git, following it's [chapter on internals](https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain). Any edit to a file generates a new object with a key, and in Git the key is a hash of the content. We could consider a file == characteristic in a topic map. Then in Git, a set of such objects are added to a tree object, which is like a folder of files. And then a commit attaches some metadata (who, when, why and what came before) to a tree object. A commit can also be considered a "changeset", that is, a set of changes across a file system.

Git doesn't directly store the deltas, but rather the full copy of a change, even if just one letter changed. Then however, it uses compression and packing format to reduce the storage on disk.

So let's see how the analogy goes. We edit a characteristic by creating a new characteristic. This new characteristic gets a unique topic added to it's scope. We can simplify away the objects and trees and just make the unique topic a commit. We could even add some the metadata to the topic as occurrences and we can point to the previous commit with an association. If we list all commit topics by their creation time, we get something akin to `git log`. We can add the commit topic to our positive context and see only the edits of that particular change, across a topic or a topic map.

Now, in reality, we most often just want to see the latest revision of everything. A way to do this can be to add an `archive` topic to the scope of an occurrence that is no longer the latest. In that way, we can have a negative context including `archive` which would remove any historical characteristics and only show the latest. So in the end, a historic characteristic would have two scopes `[commitXYZ, archive]` while a current would have just `[commitXYZ]`.

Git does this a bit differently - each tree object contains pointers to all the files in the directory as they looked at that time. That includes pointers to files that were not changed in that commit, just pointing back to *their* latest changed state. 

Questions:
- Do we need to browse revisions on topic map level or just on topic level?
- Do we need to see just changes or the full state at any given revision?
- How do we "fold in" older changes below newer changes of the "same" characteristic, considering they lack an id so there is no strict way to determine what is "same"
- How do we represent removed occurrences? (an empty occurrence?)