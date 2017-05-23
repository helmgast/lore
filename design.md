Design
==================================================================

_This working document describes the internal design of Raconteur. It is not fully up to date with the code, and features described here may also not exist yet. Try to add a **(TODO)** marker near those sections!_

Known issues
==================================================================
- In new dev, Order does not contain shipping_mobile anymore. This will generate an error. Solution is to remove all shipping mobile fields from db.
- Getting ```(E11000 duplicate key error index: rac-mirror.product.$product_id_1 dup key: { : null })``` errors when doing normal DB operations and mongoengine tries to do "ensure_index" or when inserting new. This is when a field is set as unique, but it contains several null values, for example when a new unique field is created and there is no existing data in the old db. The solution is to set the key to sparse, and remove it if we know that the index always has data.


Fablr 1.0 notes
==================================================================
Below is a list of refactoring planned for the Fablr 1.0 release.

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

New join/login flow:
First ask "who are you? (email)". When email is typed, if joining, optionally find public info tied to the email (gravatar?). Then ask "Prove it's you" (you can prove with either google, fb, password or simply getting a verification email that gives temporary access). It's possible for a user to have multiple authentication methods.
An email has status of "verified" or not. If not verified, user has to click a link in an email, or the social login has same email, which also verifies the email.
Optionally, when logging in, typing the email can also show who you are and which methods of logging in was used.
This method makes it more fluid to go between having just an email address, and having a fully registered, authenticated user.


1) "Enter email"
2) _Depends on user exists_
    2.1) "Welcome back NN, prove you are you"
        2.1.1) Select Google, Facebook, Password or Email Token (fine print)
        2.1.2) Optional: Provide extra details
        2.1.3) Logged in - redirect
    2.2) "Welcome to join, prove you are you"
        2.2.1) Select Google, Facebook, Password or Email Token (fine print)
        2.2.2) _Check if email verified (would only be if email same in G/FB)_
            2.2.2.1) "We need to make sure you own this email, check email"
        2.1.2) Optional: Provide extra details

A complete view object
==================================================================
All data required to represent a view of a resource
```
resource # which resource
plural_name
supported_operations # edit, view, etc

args # all arguments received from url
-> filter
-> order_by
-> q # search query
-> ids/slugs
-> output

default_args # default values for args, if not provided
accepted_args # arguments that are accepted

formclass # form based on the resource
extra_formfields # formfields used only by this view
field_permissions # which fields can be accessed by whom

# Alias: a url that uses another route's view but with some possible other arguments. E.g. /cart -> order/edit?order_by=title
```

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

Resource lists
------------------------------------------------------------------
Resource lists support a number of common operations as defined by the parameters above. Let's look at them in some more detail.
- Page: This shows the current page.
- Order By: This orders the results (ascending) by the field of the given name. In a table view, this is typically linked from the column header.
- Filter: This filters the results to only include items that match the filter. The filter is defined per field, and the default meaning is that the value has to be equal. If the field name is followed by a suffix such as
`__lte` it will be "larger than or equal".
- Search: Freetext search across all fields.


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

Some authorization patterns
------------------------------------------------------------------

All instances can be operated by CRUD (Create, Read, Update, Delete). For some assets,
Read is split into subvarieties, e.g. Read Published, Read Unpublished.

There are 5 types of roles:
- Admin: Have full rights to modify all resources.
- Editor: Have full rights on a specific resource, and all child resources (what is a child depends)
- Reader: Have access to read specific resources regardless of their state, and to read all child resources.
- User: Have access to create new resources and read published resources. 
(When a new resource is created, that user counts as Editor of the new instance)
- Visitor: Un unauthenticated user, can only read published resources.

Subsequently, most instances have the following states:
- Draft: not published, but in various stages of edit. glyphicon glyphicon-inbox
- Revision: not used but reserved to denote older revisions of a resource glyphicon glyphicon-retweet
- Published: Published to all with general access (typically visitors) glyphicon glyphicon-eye-open
- Private: not used but reserved to mean published to selected readers only glyphicon glyphicon-eye-close
- Archived: passed published, and now hidden from general access. glyphicon glyphicon-folder-close

Public listing:
- Public listings means to show resources with Published state, created_at an earlier time (e.g. not future dated).
- An admin/editor would see all resources regardless of state and created_at.
- A reader would see Draft, Private and Published resources.

Listing: A visitor can list a resource if the Model (not resource) allows it, e.g. if it's public or not.
If the listing can be considered listing subresources of another Model, this can also be checked.

Creation: A user can by default create new resources if the Model (not resource) allows it. In addition, if the creation
of the resource creates a link to another resource, we can check that this is allowed.

Example scenarios for authorization
---------

/thepublisher (editor: NF, reader: PN)
    /worlds
    /theworld (editor: MB, reader: AW)
        /articles
        /thearticle (editor: PF, reader: PD)
    /products
    /theproduct
        
/thearticle can be read by PD, PF, FJ, MB, NF and MF but no one else regardless of status.
/thearticle can be updated/deleted by PF, MB, MF
/anewarticle can be created by MF, MB if closed, otherwise by any user
/theotherarticle can be read by anyone if published, otherwise by PF, FJ, MB, NF and MF.
For /theworld/articles:
All users, incl PD and PF, will see only published articles.
FJ, MB, NF and MF will see all articles.

For /thepublisher/articles:
All users, incl PD, PF, FJ, MB will see only published articles without worlds. However, 
for articles with theworld visibility will be as previous example.
MF, NF will see all articles.

/theworld can be read by FJ, MB, NF, MF if not published, otherwise by all
/theworld can be updated/deleted by MB, MF
/anewworld can be created by MF

NF = Niklas Fröjd = niklas@helmgast.se
PN = petter@helmgast.se
MB = marco@helmgast.se
AW = anton@helmgast.se
PF = per.frojdh@gmail.com
PD = paul@helmgast.se
user = niasd@as.com


Roles: Admin, Editor, Reader, User, Visitor
Actions: Create, Read Published, Read Unpublished, Update, Delete

new: user
list: is_visitor

read: reader (also checks admin, editor)
edit: editor (also checks admin)
delete: editor




REST Gotchas
--------------
Things that needs some implementation thought or should be covered by frameworks used:

- Nice URLs do not match REST urls, as may want to see parent resources and no "articles" verb in the URL
- Human users have two kinds of GET - get to read, and get to edit, e.g. a form. Thereby "intent="
- Some fields need to be sent to client but not editable, eg. slug
- Some fields need some form of serialization to fit into a FORM and back into an object
- Some fields can be editable but not sent to client, e.g. password
- Creating a reference in a field to another resource may depend on permissions from that other resource (e.g. to make
an article inside a world needs permissions on that world)
- There are multiple "Schemas": one for database models, one for forms, one for URL arguments, and potentially one for auth. 
They should be kept as close/same but also have different behaviour. The DB model needs all fields while a form maybe SHOULDN'T
contain all fields.
- REST says that POST for new resources should happen on the list route e.g /articles/. It means the function that deals with that 
list route has to also deal with the logic for posting. Especially as the form for creating a new resource needs to come from the GET route.
I solved it with having the special id "post" so that the GET route can be re-used.



Forms
==================================================================

The form library is seemingly simple but infinitly complex when you scratch the surface. First, here are the components:

- WTForms (package `wtforms`) - a generic library for building Form objects that can parse and validate data before filling up the real model object with it.
- Flask-WTF (package `flask.ext.wtf`) - a mini library that joins the WTForms with Flask, such as automatically adding CSRF tokens (security)
- Flask-Mongoengine (package `flask.ext.mongoengine.wtf`) - Comes with the automatic translation of Mongoengine Document objects (Model objects) into Forms by calling model_form() function, and also makes it easy to enhance an app with the Mongoengine layer.
- Mongoengine (package `mongoengine`) - Used by Flask-Mongoengine but does the real work.

This is the lifecycle steps:

1) Create Model class (Document)
2) Create Form class by telling model_form to parse all fields in Model class, and pick suitable HTML form fields that match each variable.
3) When you have a request for a form, instantiate the Form class for that model, and by calling each field of the form, render the HTML. If the Form was instantiated with a model object, the form will be pre-filled with real model data.
4) When you get a form post response back, let the form self-parse the request data, and then if it validates, tell the form to populate a Model object with the new data (overwriting any old data).

Managing form data
------------------------------------------------------------------

Each field at the time of submission of a form can be:
- Fully writable (any data in the form, if valid, will be set as new model value). This is default WTForm behavior.
- Pre-filled and writable (a variant of above, but we pre-fill with suggested data)
- Not writable (the field is visible, but set to "disabled". Any incoming formdata for this field has to be ignored)
- Excluded (the field is not in the HTML form, any incoming data has to be ignored.)
This is not a static setting for the field. In one context, a field may be writable but in another not. For example, only an admin may be able to change certain fields, or they may only be editable if they haven't been given a value before.

Available WTForm API:
- `Form(formdata, obj, data, **kwargs)`. formdata is the data in a POST request. obj is an existing model object. data is a dict, and kwargs is additional arguments. They will not merge, e.g. they will only be applied if the previous left-wise argument was empty. So if formdata is provided, none of the other args will apply.

Issues
------------------------------------------------------------------

EmbeddedDocuments in a Model is mapped as a FormField, which is a sub-form that pretends to be a field. So you get a recursive type of behaviour. Some of the problems:

**Issue**: CSRF tokens are automatically added by flask-mongoengine using the Form class from flask-wtf. This means also sub-forms get their own CSRF which is incorrect.
Solution: We can give model_form a different ModelConverter class, which contains the functions that map a Model field to a Form field. Here we can have a subclass that changes the behaviour of the function that creates FormFields (sub forms) from EmbeddedDocuments, to avoid using the CSRF enabled form here.

**Issue**: FormFields expect to have objects (EmbeddedDocument) to fill with data, but in some Model cases we may accept having "None" for some of the Embedded Documents. This is especially true when a model has an option of containing one of several types of Embedded Documents, but normally only one contains a reference and the others are None. This means `populate_obj()` method will throw errors, because there is no object to populate, and the form doesn't know how to create a new one just because it got form data.
Solution: Articles have multiple EmbeddedFields, that may or may not be filled with data. Actually, among them, only one should be filled with data at the same time.

A) We could make sure the default value is always an empty object rather than None. This would make FormField behave well when trying to populate, even if populating with empty fields. But it would inflate the database uneccesarily and it would make it less easy to check if there is data to display (e.g. cannot just check for None on the EmbeddedDocumentField).

B) We could keep them as None by default, but it means, when someone creates an article we need to be able to instantiate the EmbeddedDocument (as the form can't do it), and when the type is changed, we need to None the old reference and instantiate the new. This step would have to happen AFTER validation but before `populate_obj`. Because we don't have "manual" access to the steps between validation and `populate_obj`, this cannot be done in current architecture.

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

Localization
==================================================================
There are two types of internationalization - interface and content.
Interface can be automatically changed but content depends on if it's 
available in that content item. Currently, no content items support multiple
languages. There is never any reason to intentionally have different interface
and content language, but may happen if content of specific language is not available.

Language input can be in reverse order of importance:

* In HTTP header (can be multiple)
* In visitor preference (cookie or user profile)
* In URL

URL is special - it should give a 404 if the requested language is not available 
as interface (ignoring content). Otherwise, we shall build a list of languages
in order of preference, with user preference ordered first. This should be matched
with the set of languages supported by interface and content respectively.

E.g.: Header says EN, SE. User says DE. Check in order DE, EN, SE vs available
interface language (EN, SE) and content (SE).

Language output is in form of:

* Displayed interface language
* Displayed content language
* Language code in HTML header
* Preselected language in relevant forms

In addition, location means which country the visitor is likely from. Location 
can be used to prefill address fields and currency.

Themes
==================================================================

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
        
       
Social users: 60%
Password: 40%
Different emails on social and pass? 30%
Login on multiple devices: 50%

Will see migration screen but already migrated:
50%

Will end up with different accounts if not migrating:


    
Migration procedure1:
1) Invalidate all previous sessions
2) If no "auth0_migrated" cookie AND no uid in session, redirect to migrate at login
3) When authenticated, store u2m (user to migrate) in session, then show signup form and avatar
4) At callback,
    a) if u2m exist in session, merge auth to that user and remove old auths, set auth0_migrated cookie and remove u2m
    b) if uid does not exist in session, but we have verified email in auth, merge with that account if it exists
    c) if uid does not exist and no email match, create new user
    Complete login and session.
   
Migration procedure2:
0) Invalidate all previous sessions
1a) If no session, show login screen as usual
1b) If session, do not link to login, but if accessed, show current user and message that we will add an auth
2) Login using email or social.
3a) If current session:
    If new auth doesn't match session user, add it and show profile with updated data.
    If new auth does match session user, and 
    If new auth does match session user, and user is invited, delete that user and merge to current user.
    If new auth does match session user, and user is active or deleted, report an unresolvable error and contact info@
3b) If no current session
    If new auth matches existing user and auth is same, just login.
    If new auth matches existing user, and auth is new, add it and show profile with updated data.
    If existing user, and new auth, show a message that we added a new profile.
4c) If existing user, and old auth, show profile and a message that user have been migrated.
4d) If not existing user, send user to "post user" page.


If press Cancel, 

Cookie includes:
email: authenticated email from auth0


Show instructions if to merge if this was unintended.

Need to always check that a user is active when verifying a logged in user, in order to be able to lock out users centrally.

How to merge:
1) We just created b@b.com (uid234) but old user is a@a.com (uid123).
2) User requests to add email a@a.com. Email verification is sent.
3) When code is entered, we will go to login but find that login for a@a.com maps to different uid123 than current session (uid234).
But it means user controls both accounts. 

    
        
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


#Markdown

----
```
![Alt](/link/image.jpg)
```
is rendered as:
```
<img src="/link/image.jpg" data-caption="Alt" alt="Alt">
```
CSS renders it to a full width image without visible caption, converted back as-is.

----
```
- ![Alt](/link/image.jpg)
```
is rendered as:
```
<ul>
<li><img src="/link/image.jpg" data-caption="Alt" alt="Alt"></li>
</ul>
```
and is converted back as:
```
- ![Alt](/link/image.jpg)
```

----
```
- ![Alt](/thumb/image.jpg)
```
Is rendered as a link to original with a thumbnail image.
```
<ul>
<li><a href="/orig/image.jpg" title="Alt"><img src="/thumb/image.jpg" alt="Alt"></a></li>
</ul>
```
Converted back as:
```
- [![Alt](/thumb/image.jpg)](/link/image.jpg)
```
----
```
- Some text ![Alt](/link/image.jpg) more text
- ![Alt](/thumb/image.jpg)
```
A list that contains any text outside an element should be treated as a normal list,
e.g. no management of images.
----

```
[Embed](http://oembedsupported-url.com/asd)
```
Rendered as:

```
<iframe ...><a href="http://oembedsupported-video.com/asd">Embed</a></iframe>
```
Rendered back as:
```
[Embed](http://oembedsupported-url.com/asd)
```
----
```
[File](/link/file.ext)
```
Rendered as:
```
<a href="/link/file.ext">File</a>
```
Based on ext, CSS will show this as a file icon.

----

```
![Alt](/link/image.jpg#center|wide|side)
```
Rendered as a normal image, but the center|wide|side (one of) is a hint on where to position it on
the page. center is default and refers to an image that spans the full column width. 
Wide is an image that covers the full page width, but is limited in height for a narrow
aspect ratio. Side is a right aligned box that the text flows around.
If the hint is applied direct to an image it will affect the image. If it's in a list,
the list will be positioned instead. The list will follow the first hint it finds.


In the UI, any inserted file or image becomes a list, and any list that is clicked 
opens a modal to pick which items on that list. So gallery lists cannot be edited directly

## Asset linking

Types of assets to link to:
- Raw images ```[domain]/asset/image/filename.ext```. Returns an original image asset.
- Resized images ```[domain]/asset/thumb/size-filename.ext```. Returns a resized image asset. Size is a variable that the backend determines dimensions of, e.g. wide|center|side|logo
- File link ```[domain]/asset/link/filename.ext```
- File download ```[domain]/asset/file/filename.ext```