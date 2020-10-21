## Text search

For text search, Mongo supports [these languages](https://docs.mongodb.com/manual/reference/text-search-languages/), at time of writing:
danish	da
dutch	nl
english	en
finnish	fi
french	fr
german	de
hungarian	hu
italian	it
norwegian	nb
portuguese	pt
romanian	ro
russian	ru
spanish	es
swedish	sv
turkish	tr

Default is english. As a collection can only have one text index so at default, the whole collection can only have one language.
You can specify a field of the document that denotes the language of each document - in that case you can search different languages.
But it means you still can't mix languages in the same document, such as having a field of translations. Of course, you can still search, but word stemming won't work.

## Collation

Collation is the use of language-specific rules for sorting fields (both text and numeric). For example, should a and A be sorted as the same or differently, should "the" or other leading characters be ignored, etc. It has a lot of rules and wide support for languages: https://docs.mongodb.com/manual/reference/collation-locales-defaults/#collation-languages-locales

You can set a collation as default on a collection (but can't change it later). You can also set a collation on an index, and on just a specific operation. But the operations collation must match the collation on the index or the collection, if set. This means, if you want to set collation as default you can't practically change it so the whole collection will have to stick with one language.
You seem to be able to use a non-collated index with a temporarly collated operation, however. 