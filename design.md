Design
==================================================================

_This working document describes the internal design of Raconteur. Note that features described here may not exist yet, and in general, try to add a **(TODO)** marker near those sections!_

Domains
==================================================================

Fablr runs on fablr.co as host. Blueprints point to a path of `/<blueprint>/`, e.g. `fablr.co/<blueprint>`, for example `fablr.co/social`
Static assets are served from either `fablr.co/static` or from `asset.fablr.co` (TODO) . Asset allows us to use several subdomains to allow parallell download, which speeds up performance.

Worlds are special cases, as they may want to stand on their own. A world is found at `<world>.fablr.co`. Some world publishers may have purchased their own domains. As such, they may want to point `publisherdomain.com` to `publisherdomain.fablr.co` and they may even have other worlds pointing to `sub.publisherdomain.com`.(TODO: publisher feature)

The only place host matters is to match the URL route to a correct endpoint, and when creating URLs using `url_for`. Also, when we use `<world>.fablr.co` it's important that `fablr.co/world` redirects to `world.fablr.co` . Also, when we use a publisherdomain, it's important that world.fablr.co still exists and redirects to publisherdomain. We need to consider `canonical URLs`, that is, the corret master URL - Google penalizes duplicate content without correct markup.

Creating routes with hostname can be created by:

    @app.route('/', hostname=<worldslug>)
    @app.route('/<worldslug>', hostname=<worldslug>)

Resources and REST
==================================================================
The server has Model classes that defines the data representation of the objects used in the system. Almost all our model classes can be called `Resources`. With Resource, we mean a model that will be exposed to the client either over the REST API or over the HTML templates.

A Model is defined with Fields of various types. An Instance is a Model with one set of specific data. Some Fields may be a Collection of other Model Instances, or a single reference to another Model Instance. All Model Instances have an ID, but most also have a Slug, which is a humanreadable identified based off the name or title of the Instance.

Internally, we have built the `resource.py` library to deal in a similar way with all models. That allows us to make generic functionality no matter we are dealing with a User, Article or World. Note however, that not all model objects are used as resources and not all URL routes are served as resources!

Let's start with the formal REST design:

    GET    /people               list members
    POST   /people               create member
    GET    /people/1             retrieve member
    PUT    /people/1             replace member
    PATCH  /people/1             update member
    DELETE /people/1             delete member

We have based ours on above but with some modifications. One modification is that we will often serve over an HTML "API" that can only send GET and POST, so we need some additional logic for that. Another reason is that we readable URLs.

Our resource URL scheme looks as follows:

    GET     /<resources>            list        list members
    GET     /<resources>/new        form_new    get form for new resource
    POST    /<resources>            new         create resource
    GET     /<resource>/<slug>      view        get resource
    GET     /<resource>/<slug>/edit form_edit   get resource as form
    PUT;POST    /<resource>/<slug>  replace     replace resource
    PATCH;POST  /<resource>/<slug>  edit        resource
    DELETE;POST /<resource>/<slug>  delete      delete resource

`<resource>` is the name of the resource in singular. `<resources>` is the name in plural. `<slug>` is normally the human readable but unique identified, but it can in some cases also be an `id` (a MongoDB ObjectID).

Some variations to the URL scheme:

    /<resource>/<slug>/<other_resource>/<slug>new   a hierarchy of resources
    /<slug>/<other_slug>/new                        shortened URL structure
    <slug>.domain.com/<other_slug>/new              shortened URL, with subdomain

E.g.

    GET world/worlds <- list worlds
    POST world/worlds <- create new world
    GET world/<worldid> <- static world view
    PUT,PATCH,DELETE world/<worldid> <- modify world
    GET world/<worldid>/articles <- list articles
    POST world/<worldid>/articles <- create new article
    GET world/<worldid>/<articleid> <- static article view
    PUT,PATCH,DELETE world/<worldid>/<articleid> <- edit article

**Notes**
- For basic HTTP browsers that don't support all verbs, we also accept POST, with the param ?method=PUT, PATCH, etc and interpret it as above

Arguments
------------------------------------------------------------------

Most endpoints also support URL arguments to tailor the request. Below we list the current ones.
Special note on ?out . ?out=fragment means that we return HTML, but only the content part. What exactly is defined as the limits of the fragment depends on the view, but overll, fragments are intended to replace a part of HTML with new data. ?out=json means we get the query representation in JSON.

    GET     /<resources>            list        
                                    return_type ?out=full (default)
                                                ?out=fragment
                                                ?out=json
                                    ordering    ?order_by=<field>
                                                ?order_by=-<field>
                                    filtering   ?<field>=<val>
                                                ?<field__gt>=<val>
    
    GET     /<resources>/new        form_new    get form for new resource
                                    return_type ?out=full (default)
                                                ?out=fragment
                                                ?out=json
                                    prefilling  ?<field>=<val>
                                                ?<field__gt>=<val>
    
    POST    /<resources>            new         
                                    next url    ?next=<url>
    
    GET     /<resource>/<slug>      view        get resource
                                    return_type ?out=full (default)
                                                ?out=fragment
                                                ?out=json
    
    GET     /<resource>/<slug>/edit form_edit   get resource as form
                                    return_type ?out=full (default)
                                                ?out=fragment
                                                ?out=json
                                    prefilling  ?<field>=<val>
                                                ?<field__gt>=<val>
    
    PUT;POST    /<resource>/<slug>  replace     replace resource
                                    next url    ?next=<url>
    
    PATCH;POST  /<resource>/<slug>  edit        resource
                                    next url    ?next=<url>
    
    DELETE;POST /<resource>/<slug>  delete      delete resource
                                    next url    ?next=<url>

Errors
==================================================================

Responses
------------------------------------------------------------------
    200     Rendered output as per argument
    400     Bad request (general error or incorrect validation)
            If on HTML, we can just highlight the errors on the page
    404     Not found (given resource id does not exist)
    401     Unauthorized (not logged in or not access to article)
            If on HTML and not logged in, send to login page first
    403     Forbidden (operation is not allowed)
    500     Internal Server Error (python exception)

Error inputs:
- Not found
    - API error
    - Partial error
    - Error page
    - Logging
- Not authorized
    - API error
    - Partial error
    - Error page
    - Logging
- Server error
    - API error
    - Partial error
    - Error page
    - Logging
- Malformed request
- Form doesn't validate

Output:
- API JSON error
- Partial-HTML response error (as attached JSON)
- Flash (as response to POSTs or on-page errors)
- Logging
- Debug exception
- Error page

**If request full html**

    400     -> bad request
            if a edit/new of form, return original form with validation errors highlighted in requsted form and flash message shown
            if error with URL args, just flash message
    401     -> Unauthorized, redirect to login-page if not logged in, else flash message not allowed
    403     -> forbidden operation, just flash message that not possible with current user
    404     -> not found page
    500     -> flash message about internal server error
            if debug, go to debug instead

**If request fragment**

    400     -> bad request
            if a validation error, return fragment html of complete form with validation errors
            else return text line to insert into flash
    401     -> return flash message that "need to be logged in (with a link to click?)"
    403     -> forbidden, return flash message that not possible
    404     -> return flash message
    500     -> return flash message

**If request json**

    400     -> bad request
            if validation error, return json representation of form.errors
            else return normal json error dict
    401     -> unauthorized, return json error dict
    403     -> forbidden, return json error dict
    404     -> not found, return json error dict
    500     -> return json error dict


Flow
------------------------------------------------------------------
_TODO Not fully up to date with current code_

    0) For a given URL and METHOD, map to function
    1) Map method to actual view function (POST SR)
    2) Expand url params
        if method, call corresponding function
        if incorrect, respond 400
        else proceed
    3) Get all resources instances from ids and authorize user
        if not found, respond 404
        if not authorized, respond 401
        Else
            a) Render static view of resource (GET SR, GET PR)
                a) GET SR/ Render SR
                    Respond 200
                b) GET PR/ Parse and validate listing args
                    If incorrect listing args
                        Respond 400
                    Else continue
                        Respond 200
            b) Render form view of resource (GET SR/edit, GET PR/new, GET PR/edit)
                a) GET SR/edit Create form object, render form
                    If incorrect prefill fields, ignore, respond 200
                b) GET PR/new Create form object, render form
                    If incorrect prefill fields, ignore, respond 200
                c) GET PR/edit Parse and validate listing args, render as editable
                    If incorrect listing args
                        Respond 400
                    Else continue
                        Respond 200
            c) Validate input, commit to model, render response (POST;PUT;PATCH;DELETE SR/, POST PR/)
                Create form object, input
                If DELETE)
                    Respond 300 (to PR/)
                Else if Validate
                    If POST)
                        1) Instantiate new model obj
                    If PUT)
                        1) Instantiate new model obj
                    Populate model obj with form data
                    Respond 300 (to SR/)
                Else
                    Return 403, form with highlighted validation errors

Auth
==================================================================

The authorization system is there to limit access on the Raconteur system. It's represented in a few ways:
- Limiting access to Operations / URLs and throwing a 401 error
- Conditionally displaying links / html fragments only if the user is authorized to see it

`Resource.py` defines 8 standard operations on a resource, and they can all be generally classified as read or write operations. A certain resource can be readable by everyone or only specific groups, as well as writable. The exact logic for deciding authentication this depends on the resource.

The key to this is the function `ResourceStrategy.allowed(op, instance)` op is the current operation being tested instance refers to the specific instance of a resource, as most ops act on an instance. If the op does not act on instances (e.g. list, new), it is not needed. The user is automatically read from the` flask.g` object that keeps the current session. `allowed()` will automatically throw a `ResourceError` if the user is not allowed.

For templates, there is the macro called IS_ALLOWED() which works in a very similar way but doesn't throw exceptions and instead just outputs what's inside the macro if allowed, otherwise not.

Access to resources are normally given to groups. A group is a list of users, where there are "members" and "masters". By default, members will have read access, masters have write access, and non-members no access. Each resource has a special "group" which is the creator group, which normally means
the user who created the resource, if this is a field existing in the resource. 

    Login: Create/refresh logged in session for an existing user.
    If user is not completed or if google auth works but no user, send on to verify. If user exist and auth correct, redirect to next. Otherwise throw error.
    
    GET: 
         IF: not logged in, just show message with logout link
         ELSE: show FORM
    POST:
        IF: Logged in, just show message with logout link
        ELSE:
            IF: google_code # received google code
                connect_google
                IF success
                    IF user exists
                        login_user w/ google details
                        return JSON to redirect
                    ELSE # no user, must connect to existing user or make new
                        TBD
                ELSE
                    return JSON error
            ELIF formdata
                IF valid and user exists
                ELSE
                    return error
            
         ELSE: 400
    
    Join: Create a new user.
    Create a new user from scratch or from external auth. Create in unverified stage before email has been confirmed.
    
    Verify: Complete registration of a previously created but incomplete user.
    Same as join more or less, but assumes user exists but needs additional info. If email and token are given, verify user.

Some access patterns
------------------------------------------------------------------

- User. Read by all (if system-activated), write by user or admin.
- Group. Read by all, write by group master or admin.
- ImageAsset. Read by all, write by creator or admin.
- Article. Read by those in Readgroup, Write by those in write groups.
- World. Read by all, write by world creator group or admin.

Login-flow
------------------------------------------------------------------
A user can currently be either Invited, Active or Deleted. The definitions:
- Invited: user exists in the database but has not verified its email, meaning it cannot be considered secure (someone can send up with another persons email). No communication can happen with an invited user, except to verify the email.
- Active: A normal user. Must have at least one authentication method.
- Deleted: A user that has been removed but is kept in database to keep consistency. Can theoretically be re-activated.

1) Join: A visitor goes to /auth/join to create a new user. He/she provides
an email (required) and then chooses to authenticate with Google, Facebook or
Password.



Forms
==================================================================

The form library is seemingly simple but infinitly complex when you scratch the surface. First, here are the components:

- WTForms (package `wtforms`) - a generic library for building Form objects that can parse and validate data before filling up the real model object with it.
- Flask-WTF (package `flask.ext.wtf`) - a mini library that joins the WTForms with Flask, such as automatically adding CSRF tokens (security)
- Flask-Mongoengine (package `flask.ext.mongoengine.wtf`) - Comes with the automatic translation of Mongoengine Document objects (Model objects) into Forms by calling model_form() function, and also makes it easy to enhance an app with the Mongoengine layer.
- Mongoengine (package `mongoengine`) - Used by Flask-Mongoengine but does the real work. 

This is the lifecycle steps:

1) Create Model class (db.Documents)
2) Create Form class by telling model_form to parse all fields in Model class, and pick suitable HTML form fields that match each variable.
3) When you have a request for a form, instantiate the Form class for that model, and by calling each field of the form, render the HTML. If the Form was instantiated with a model object, the form will be pre-filled with real model data.
4) When you get a form post response back, let the form self-parse the request data, and then if it validates, tell the form to populate a Model object with the new data (overwriting any old data).

Issues
------------------------------------------------------------------

EmbeddedDocuments in a Model is mapped as a FormField, which is a sub-form that pretends to be a field. So you get a recursive type of behaviour. Some of the problems:

**Issue**: CSRF tokens are automatically added by flask-mongoengine using the Form class from flask-wtf. This means also sub-forms get their own CSRF which seems exxagerated.
Solution: We can give model_form a different ModelConverter class, which contains the functions that map a Model field to a Form field. Here we can have a subclass that changes the behaviour of the function that creates FormFields (sub forms) from EmbeddedDocuments, to avoid using the CSRF enabled form here.

**Issue**: FormFields expect to have objects (EmbeddedDocument) to fill with data, but in some Model cases we may accept having "None" for some of the Embedded Documents. This means `populate_obj()` method will throw errors, because there is no object to populate, and the form doesn't know how to create a new one just because it got form data.
Solution: Articles have multiple EmbeddedFields, that may or may not be filled with data. Actually, among them, only one should be filled with data at the same time.

A) We could make sure the default value is always an empty object rather than None. This would make FormField behave well when trying to populate, even if populating with empty fields. But it would inflate the database uneccesarily and it would make it less easy to check if there is data to display (e.g. cannot just check for None on the EmbeddedDocumentField).

B) We could keep them as None by default, but it means, when someone creates an article we need to be able to instantiate the EmbeddedDocument (as the form can't do it), and when the type is changed, we need to None the old reference and insantiate the new. This step would have to happen AFTER validation but before `populate_obj`. Because we don't have "manual" access to the steps between validation and `populate_obj`, this cannot be done in current architecture.

C) We can change the FormField class (inherit) so that it's `populate_obj` method correctly sets only the active type's EmbeddedDocument fields to a new instance and sets all others to None.

Templates
==================================================================

When we render, we have many different scenarios to deal with. We have the following type of template files:

- Base-files. These are complete with header, footer, sidebar etc but inhering form parent category, ultimately _page.html.
- View-files. A view fills the main content part of a Base file with either a Instance, or a list of Instances. It is the response to e.g. /list, /view, etc. Most views are simply a 1-to-1 with an Instance view, e.g. user/edit for account form. As the template is very similar, the same view is used to show all operations /new, /view and /edit.
- Instance-files. These are an atomic representation of an instance. Instance can be of different types, where the default is "full". Full will typically show all the non-internal fields of an Instance. "row" will be a minimal representation based to fit into a table, and "inline" will be small view/form intended to be shown in modals or similar. As the instance files are re-usable across views, the views should only refer to instance-files.

Template structure
------------------------------------------------------------------

    _page.html
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

    _page.html
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
    {% extends _page.html if not template else template}

Example
------------------------------------------------------------------
Model Article consists of following fields:

- title (char)
- world (->model)
- content (text)
- type (choice)
- persontype (<-model) (an associated model)
- article relations (->*models) (collection of relations)

In /view?form=fill it will render as:
    
    Name: {{name}}
    World: {{world}}
    Content: {{contet}}
    Type: {{type}}
    Subform:Persontype
    Subform:Relations

In /edit?form=full, it will render as (simplified):
    
    <input name=char/>
    <select name=world/>
    <textarea name=content/>
    <select name=type/>
    <?subform?/>
    <multiselect name=relations>

- Full forms can come as a complete HTML form with Submit and Cancel buttons.
- Inline forms can come as smaller popups (if they are the same size as full form, one may as well call edit/?inline) or as parts of other forms. They can be loaded dynamically into pages or modals. They will not come with their own form and submit buttons, so need to be placed in a container classed .m_instance, so that we can use jQuery to figure out when to post parts of a form.
- Row forms are assumed to exist within a table, or more generally speaking, a list of instances. The form could still work as normal, which means the user can edit the (exposed) fields of the instance, like an Excel-sheet. The top container of the form representing a unique instance should have the class *.m_instance*. As we cannot rely on normal form logic (it would post the whole page) we must use jQuery to post the contents of this form, and this has to be triggered from a submit event that either comes from the form itself (embedded save button) or that comes from a parent container (e.g. a save button in the top of the table). However, commonly the row form can be accessed as /view, which means it's static. However, it can still be part of operations, or rather the list can have operations: add and remove. Add should fetch a new row and append it as well as creating a relationship model instance, remove should take away the row and delete the corresponding relationship. The adding (visually) and the adding (technically, with POST) may happen at different times.
- In-place editing. As we use the same template behind for both view and edit, it's fully possible to switch between them and load the contents using ?inline, no matter which form above it is. It's just a matter of changing /view to /edit and vice versa.

Social
==================================================================

**Forum design**

    - Forum
    -- Board
    --- Topic
    ---- Post (message)

Conversation
------------------------------------------------------------------
A conversation is a list of messages from users. The list will always be flat (not threaded) and ordered by time. A conversation can be eternal, but normally is started and held active within a certain time. A conversation has members. Members are allowed to post messages to that conversation. The conversation can be tied to different things. It can be a comment, where it is tied to a place in an article (or by default, at the bottom/top). Conversations can be grouped into topics.

**Use of conversations**

- Closed chats for a game session (all can write)
- Closed chat within a group, outside of game session (e.g. a permanent discussion)
- Public posting of messages (one writes, rest reads)
- Public discussion

World
==================================================================
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

Maintenance
==================================================================

Backup database
------------------------------------------------------------------
Run the following command
    mongo <db_name> db/backup_db.js

This will create a backup with todays timestamp.