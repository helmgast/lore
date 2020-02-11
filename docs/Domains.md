Domains
==================================================================

Lore runs on lore.pub as host. Blueprints point to a path of `/<blueprint>/`, e.g. `lore.pub/<blueprint>`, for example `lore.pub/social`
Static assets are served from either `lore.pub/static` or from `asset.lore.pub` (TODO) . Asset allows us to use several subdomains to allow parallell download, which speeds up performance.

Worlds are special cases, as they may want to stand on their own. A world is found at `<world>.lore.pub`. Some world publishers may have purchased their own domains. As such, they may want to point `publisherdomain.com` to `publisherdomain.lore.pub` and they may even have other worlds pointing to `sub.publisherdomain.com`.(TODO: publisher feature)

The only place host matters is to match the URL route to a correct endpoint, and when creating URLs using `url_for`. Also, when we use `<world>.lore.pub` it's important that `lore.pub/world` redirects to `world.lore.pub` . Also, when we use a publisherdomain, it's important that world.lore.pub still exists and redirects to publisherdomain. We need to consider `canonical URLs`, that is, the corret master URL - Google penalizes duplicate content without correct markup.

Creating routes with hostname can be created by:

    @app.route('/', hostname=<worldslug>)
    @app.route('/<worldslug>', hostname=<worldslug>)


- All static resources are served from lore.pub (core domain). Later they might be served from a static top domain to
avoid using same credentials. With HTTP2 the need to do this is less or even counter productive however.
- All asset links (e.g. semi-static resources) are also served from lore.pub for simplicity. Note however that these might
need credentials to be served.
- lore.pub is the landing page about the platform
- lore.pub/auth
- api.lore.pub is where the common API (will be) hosted
- lore.pub/mailer is used for sending email
- publisher.com or publisher.lore.pub is a complete subset of pages. All data served with such a domain will be bound
to either come from that publisher, or where it's not relevant, served anyway. Such routes are:
-- worlds/ (public)
-- articles/ (public)
-- products/ (public)
-- orders/ (login)
-- fileassets/ (login, refers to the upload and editing, serving is from separate)
-- users/ (public)

If a route above is visited with the core domain (lore.pub) no filtering per publisher is made.