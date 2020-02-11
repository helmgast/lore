Lore 1.0 notes
==================================================================
Below is a list of refactoring planned for the Lore 1.0 release.

- Use https://github.com/hansonkd/FlaskBootstrapSecurity as basis
- Implement Flask-Security (but keep our social logins)
- Doing above will likely need new hashed passwords, which means we need some migration codes to let users with old passwords automatically re-hash at next login.
- Implement HTTPS
- Implement Flask-Scripts (convert form setup.py and built-in ones)
- Implement Flask-Bootstrap (for slightly simplified templates)
- Change routes to Views as per Flask views
- Add caching (with memcached)
- Adds unittesting
- Using Flask Assets for css
- Upgrades Flask WTF
- Move all blueprint related classes (except maybe templates) into each blueprint directory
- Move python code into subdir of repo (important for file access security)
- Refined access control using Flask-Principal, and include turning on and off parts of website
- Move user from social, and de-activate social, campaign and tools (keep as separate branch/blueprint)
- Deploy in Docker or similar

        
URLs

GET/POST    api|/articles/
GET/DEL/PAT api|/articles/<article_id>
GET/POST    api|/worlds/
GET/DEL/PAT api|/worlds/<world_id>


Human friendly URL
GET/DEL/PAT     <pub>|/<world or 'meta'>/<article>
GET/POST        <pub>|/<world or 'meta'>/articles/
GET             <pub>|/<world or 'meta'>/[home, articles, blog, feed]/ <- specific views, translates to set of args on world/


GET/DEL/PAT     <pub>|/<world>
GET/POST        <pub>|/worlds/
GET             <pub>|/[home, articles, blog, feed]/



