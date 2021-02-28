# Templates

When we render, we have many different scenarios to deal with. We have the following type of template files:

- Base-files. These are complete with header, footer, sidebar etc but inhering form parent category, ultimately \_root.html.
- View-files. A view fills the main content part of a Base file with either a Instance, or a list of Instances. It is the response to e.g. /list, /view, etc. Most views are simply a 1-to-1 with an Instance view, e.g. user/edit for account form. As the template is very similar, the same view is used to show all operations /new, /view and /edit.
- Instance-files. These are an atomic representation of an instance. Instance can be of different types, where the default is "full". Full will typically show all the non-internal fields of an Instance. "row" will be a minimal representation based to fit into a table, and "inline" will be small view/form intended to be shown in modals or similar. As the instance files are re-usable across views, the views should only refer to instance-files.

## Template structure

```
{% raw %} # needed for Jekyll to not get stuck on Jinja tags
    _root.html
        section.html
            model.html

    <model>_form
        if partial then extend partial else extend "world.html"
        block: in_page
        block: in_table
        block: in_box
    <model>_view
        extend page, table, box
        block: content
        block: in_table
        block: in_box
    <model>_list
    <model>_custom

    _root.html
    ---------

    <html>
    <head></head>
    <body>
    {% block body %}
    {% endblock %}
    </body>
    </html>

    mail.html
    ---------
    <html>
    <head></head>
    <body>
    {% block body %}
    {% endblock %}
    </body>
    </html>
    # As above, but with some specialities for mail

    modal.html
    ----------

    <div class="modal-header">
      <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>
      <h4 class="modal-title">{% block content_title %}{% endblock %}</h4>
    </div>
    <div class="modal-body">
      {% block content %}{% endblock %}
    </div>
    <div class="modal-footer">
      {% block footer %}
      <button type="button" class="btn btn-default" data-dismiss="modal">{{ _('Cancel') }}</button>
      <button type="button" class="btn btn-primary modal-submit" data-loading-text="Loading...">{{ _('Insert') }}</button>
      {% endblock %}
    </div>
    {% block final %}{% endblock %}

    fragment.html
    ----------
    {% block content %}{% endblock %}

    resource_item.html
    {% extends _root.html if not template else template}

{% endraw %} # needed for Jekyll to not get stuck on Jinja tags
```

## Themes

- What is not themeable (at start):
  - Navbar (except navbrand)
  - Footer
- What can be themed
  - page-header
  - page (container)
  - 3 types of fonts:
    - Base font (body)
    - Header font (h1-h7)
    - Article font (article)
