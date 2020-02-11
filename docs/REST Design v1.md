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

REST Gotchas
--------------
Things that needs some implementation thought or should be covered by frameworks used:

- Nice URLs do not match REST urls, as may want to see parent resources and no "articles" verb in the URL
-- separately create nice URLs as shallow alias to API calls
- Human users have two kinds of GET - get to read, and get to edit, e.g. a form. Thereby "intent="
-- make all editable pages automatically activate into edit mode, not loading a separate page
- Some fields need to be sent to client but not editable, eg. slug
-- a schema setting
- Some fields need some form of serialization to fit into a FORM and back into an object
-- serialize into json and make the form component deal with it
- Some fields can be editable but not sent to client, e.g. password
-- special case, but schema setting. in Eve, set projection for fieldname to 0
- Creating a reference in a field to another resource may depend on permissions from that other resource (e.g. to make
an article inside a world needs permissions on that world)
-- Generalized hierarchical articles system
- There are multiple "Schemas": one for database models, one for forms, one for URL arguments, and potentially one for auth. 
They should be kept as close/same but also have different behaviour. The DB model needs all fields while a form maybe SHOULDN'T
contain all fields.
-- Fixed with schema setting to hide some fields
- REST says that POST for new resources should happen on the list route e.g /articles/. It means the function that deals with that 
list route has to also deal with the logic for posting. Especially as the form for creating a new resource needs to come from the GET route.
I solved it with having the special id "post" so that the GET route can be re-used.
-- Tricky to solve. Maybe keep special "post" ID. 

### Requirements to test on an API framework:

- prefillable fields
- WTForm might be removed - replace with vue? or we generate wtform from schema
- Filteroptions, e.g how to display the possible options?
- Automatic Action URL?
- Log events (using oplog?)
- Contribution allowed is not enforced, individual ownership maybe
- Streaming GridFS-files?
- MD5-based check of media
- Filter queries based on access right?
- Reorder asset list to show selected files first
- filter based on access?
- stock count