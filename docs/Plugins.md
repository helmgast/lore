Plugins
==================================================================

A plugin is a template that is loaded on an article. The plugin cannot store any data on it's own, it can only use the API to store more data in e.g. the article.

It consists of a theme.html file that is the entrypoint. It will be added to the page template tree, e.g. will be the parent of the page template used by the article.

The theme.html may have everything inlined, or it may reference separate image, CSS and JS files.

An article can only be associated with one plugin at a time, as they would otherwise conflict inheritance.

Plugin can use blocks to change behaviour.
Block cssimports makes it possible add style or reference external CSS.
Block js adds Javascript files.

A plugin is a Github repository. We register the plugin by adding its URL to the plugin page of Lore. The first time this is done, it will download the latest commit of that repository to the folder with path /plugins/:githubuser/:repo/:commit/ .

All articles, worlds and publishers can pick a template from the list of added plugins. When it is picked, at load time, it will read the template from the path given above. The asse

Plugin publishing flows

1 Users update a Github repo. Manually reminds admin. Admin reviews code. Admin builds new Lore image with dependency.
2 Users update a Github repo. Manually reminds admin. Admin reviews code. Admin runs script/web action to fetch new dependency in runtime.
3 Users update a Github repo. Webhook is called at Lore, new version automatically fetched. Admin reviews code. Admin approves new version (removing old, switching).
4 Users update a Github repo. Webhook is called at Lore, new version automatically fetched. It is automatically published and running.
4 Users update a Github repo. Webhook is called at Lore, new version automatically fetched. It is published only for the user, but published for all after admin reviews code.

