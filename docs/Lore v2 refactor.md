# Lore Refactor

_Only one thing is constant, and that is the desire to refactor_

### Currently, Lore has some fundamental issues:

- There is no clean REST/JSON API and no API documentation
- It couples some very different concepts too closely, so that the main view code mixes forms, themes, routing, database and REST.
- It's time consuming to modify the data model, primarily due to complexity in creating forms and the frontend.
- The frontend is not offering a lot of interactivity and uses a messy jQuery code base
- Some headaches, wasted time or feeling of risk attached to operating own database, server, etc.
- A poor editing experience.

### So the goal of the re-factor would be:

- Overall philosophy: plumbing may occasionally be fun but I should spend my time on domain specific code like character forms, generating world data or creating content, not on plumbing!
- A clean frontend vs backend separation (even if the frontend happens to be rendered on the server), where the API can be used on its own.
    - GraphQL or REST?? GraphQL fits perfectly on paper but comes with a lot of new learning, bloated libraries, etc. REST is well known but comes with a lot of small quirks that we rather not get entangled in again.
- Keep or improve the ability to have one data model and generate the rest from it, preferrably with a standard like OpenAPI
    - Important to get OpenAPI or not?
    - Generate React components or something else?
- Prepare for serverless operation. If we could deploy all on Firebase or Now with one command, it would definitely save time and headache. We could avoid operating database, backups, proxy server, file system & backups, certificates, logging, analytics to a large extent.

### Desired features (old)

- Host multiple publisher domains and world name-spaces
- Configurable locale for interface language, dates and content
- Configurable proxied dev and prod environment (lore.test vs lore.pub)
- Build chain for assets
- Media stored in Cloudinary
- Login with Auth0, SSO across domains, 100s of users . (What exactly needs to be hidden behind auth?
- Google Docs as source
- Multi-level access control for all items
- Automated form validation
- Plugin system for themes using Github hooks
- Mail send on actions and for newsletters
- Deploys to docker with separated config
- Error reporting and friendly error pages
- Relation based connections between articles
- Markdown or WYSIWYG editing
- Schema based REST or Graphql API

### Tricky areas

Areas that are more tricky than it first looks, which should set the bar for what a new system can handle.

- Form validation (currently done by WTForms, but tricky with complex fields like lists, dicts, embedded)
- Form generation from model data (flask-wtf generates forms from a model class, saves lots of plumbing but makes it also hard to follow)
- Form processing for lists, maps, etc. For example order of lists, should maps with empty values but keys be set, pre-populate keys, but values, etc
- Customizing queries for what select fields should show as choices
- Internationalization
- Multi/wildcard domain behaviour

## CMS Comparison

### Paid CMS:

- Contentful - priced per user
- Prismic - priced per user
- https://www.datocms.com/pricing - user based pricing
- https://forestry.io/pricing/ - backed by Git

### Open Source CMS:

- https://www.netlifycms.org/ (Git backend but multi-user editing through "proxy server")
- https://directus.io (PHP, Mysql)
- https://strapi.io (NodeJS, Graphql, SQLite, Mongo, Mysql)
- https://getcockpit.com (PHP, MongoDB, SQLite)
- https://github.com/birkir/prime (NodeJS, Postgresql)
- https://www.keystonejs.com/ (NodeJS, Mongo, Graphql)
- https://wagtail.io/ (Python/Django, )

### GraphQL solutions:

- Prisma: Creates a GraphQL backend but you still need to write your own backend (why? e.g. to make auth)
- Hasura: Adds a layer on Postgresql which can become your complete backend for data fetching, including auth with Auth0.
- EdgeDB: A distributed DB with GraphQL built in.
- subzerocloud and postgraphile/postgraphql
