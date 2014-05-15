# Workflow
## Backup database
Run the following command
    mongo <db_name> db/backup_db.js

This will create a backup with todays timestamp.

# Design

On the server, there are Model classes that fully represent every entity in the system. The exception is that some Models represent only many-to-many relationships (meaning they are not an entity but a relationship).

Definitions: A Model is defined with Fields of various types. An Instance is a Model with one set of specific data. Some Fields may be a Collection of other Model Instances, or a single reference to another Model Instance. All Model Instances have an Id, but most also have a Slug, which is a humanreadable identified based off the name or title of the Instance.

Based on approximate REST philosophy, every Model object in the system can be acted upon. These are supported operations:

* Model->LIST: Return all (or filtered) list of Instances in Model.
* Model->NEW: Create a new Instance of the Model.
* Instance->VIEW: View an Instance of the Model.
* Instance->DELETE: Permanently delete an Instance of a Model (relationships to it may need to be dealt with)
* Instance->EDIT: Update fields in an Instance of a Model.
* Instance->Collection->ADD: Adds Instances to a Collection in this Instance.
* Instance->Collection->REMOVE: Adds Instances to a Collection in this Instance.
* Instance->Custom: Custom actions on this Instance.

##URL SCHEME
    /<model>s/?filterargs               GET:list all
    /<model>s/new                       GET:form for new        POST: create new instance
    /<model>s/<id>/                     GET:instance view/form  POST: Update Instance if form
    /<model>s/<id>/view                 GET:view of instance    POST: None
    /<model>s/<id>/edit                 GET:form of instance    POST: update instance
    /<model>s/<id>/delete               GET:user prompt         POST: delete instance
    /<model>s/<id>/<collection>/add     GET:user prompt         POST: add Instances identified in args
    /<model>s/<id>/<collection>/remove  GET:user prompt         POST: remove Instances identified in args
    /<model>s/<id>/<custom>             GET:user prompt         POST:do it

###Formal REST (for reference, not fully used here case)
    GET    /people               list members
    POST   /people               create member
    GET    /people/1             retrieve member
    PUT    /people/1             update member
    DELETE /people/1             delete member

We use GET for non-state-changing operations, and POST for state changing operations. There are some variations and considerations to note:
###GET
* GET <id>/ (without view, edit) This will either do a view or an edit depending on the access rights of the user. A shorthand.
* GET <id>/?inline or ?inline=True means server should only return inline HTML, ready to be inlined on calling page
* GET <id>/?json or ?json=True means server should only return JSON representation
* GET <id>/?arg=1&arg=2 means if we are getting a form, prefill these values (parsed as if it was a form POST)
* GET <id>/?form=xxx means that we are requesting a specific type of form, as most models can be represented by several.

###POST
* POST .../?inline or ?inline=True means we are posting from an inline form, and redirect destination should also be inline

###Errors
If there is an error with a GET or POST, it should return error information using the flash() system. If the request was inline, it should return a inline form. Else, it should return to the page it came from or other page defined. This only includes errors that are not of HTTP nature, e.g. internal ones.

##ROUTE HANDLERs
Each URL pattern - route - points to a handler, e.g. function, that performs business logic, database lookup (e.g. Model interaction) and starts rendering. Althouh each URL pattern has it's own function, not all are doing any specific operations - many redirect to a more generic handler.
So, for most Models, the mapping will be like this:
    
    /<model>s/                          --> <model>_list()
    
    /<model>s/new
    /<model>s/<id>
    /<model>s/<id>/delete               --> <model>_edit()
    
    /<model>s/<id>/<collection>/add     
    /<model>s/<id>/<collection>/remove  --> <model>_<collection>_change()

The reason is that the logic and the subsequent rendering will have many similarities for an Instance of a Model, as well as the removing or adding to a collection. *Note, this is not fully implemented and may vary!*

##TEMPLATE SCHEME
When we render, we have many different scenarios to deal with. We have the following type of template files:
- Base-files. These are complete with header, footer, sidebar etc but inhering form parent category, ultimately base.html.
- View-files. A view fills the main content part of a Base file with either a Instance, or a list of Instances. It is the response to e.g. /list, /view, etc. Most views are simply a 1-to-1 with an Instance view, e.g. user/edit for account form. As the template is very similar, the same view is used to show all operations /new, /view and /edit.
- Instance-files. These are an atomic representation of an instance. Instance can be of different types, where the default is "full". Full will typically show all the non-internal fields of an Instance. "row" will be a minimal representation based to fit into a table, and "inline" will be small view/form intended to be shown in modals or similar. As the instance files are re-usable across views, the views should only refer to instance-files.

###Example
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

###Making it work
To make above work, we need to be able to:
- Create at least one instance template per Model, up to 3 (e.g. if doing inline and row forms as well). These are coded once and placed in models/ dir.
- For the ResourceHandler instantiation to create up to 3 form classes per Model, and to be able to be told which relationships should be considered part of the model forms, and what other fields to hide as well (internal only)
- For the generic ResourceHandler handle_request on server to be able to detect:
  - What form type was requested
  - To be able to customize which fields to show if the arguments are given (e.g. customize the forms on the fly)
  - Pre-filled args
  - Hard-coded args (e.g. if a form is in a context where one of it's Model foreign keys is hard coded to the parent Model)
  - Taking POSTs where we have to create NEW instances first, and relationship instances thereafter
  - When we create new Instances that has associated Instances (e.g. relationships), we need to be able to do a GET for a new row (e.g. relation) to be added, but the server hasn't been told that such an instance exist yet. So either we have to be able to template it on client side only, or we have to be able to tell the server to do it for us, to create a dummy representation, with certain input.
- For client side script to be able to
  - Detect submit type actions on parts of forms and submit them separately
  - Or, be able to keep multiple forms together and post them all at once? (e.g. if we create new objects, we can't save relationships before we save the parent)
- Other things
  - We can't nest forms, so when we make a subform, we can't include the form tag, but if we load the subform elsewhere, it may need to include a form! How does the server know when form tags should be added or not?

### Flow
1. User visits Article page, GET article/
2. If User is allowed to edit, respond as if GET article/edit.
3. As no ?form was given, assume full form.
4. If args are given that matches form field names, attempt to pre-fill form contents
5. Load template article_full.html (or article_view.html if we need additional content outside of the Article itself)
6. As no ?inline, article_full will inherit form world.html and so on.
7. article_full will render itself, and it will include articlerelationship_row och person_article as subforms.
8. ??? how to tell client side to change person_article to e.g. place_article if user makes change?
9. As the two subforms are part of article_full, we will not need to display any fields to choose "article" - it's implicit.
9. Full page is served to user
10. User makes changes to the form. User presses button to add new articlerelationship.
11. AJAX call GET /article/relationships/new?inline&form=row
12. As we got the request as a field to article, we know that the form we serve also can have implicitly filled FromArticle as original article.
13. We will load the articlerelationship_row.html, and as we got request for inline, we will not inherit from base.html but form inline.html
14. We will respond with a form for a new ArticleRelationship, with FromArticle hidden/prefilled.
15. Response is added dynamically to the bottom of the list (alphabetical order would be very complicated!)
16. User can type in the details of the relationship as a normal form. When user is ok with edits, we could automatically POST the form in the background in order to create the relationship. The downside is that if the user changes their mind, we need to remove it again. Also, if we were working on a NEW article, there would be no real Article object to include in the Relationship. However, the client script doesn't know how to turn the form in a row into a static form to show it's completed. Either we leave the filled form as is, or we do a new roundtrip to server where we POST, attach magic id dummy to FromArticle, get redirected to a non-editable HTML snippet that we can insert back into the same place. However, we need to have jQuery remember that this change hasn't yet been commited!
17. Finally, user saves the complete Article. We will need to include all subforms, and on server side, we need to be able to break them up into representations of separate objects again.


World
	id # is slug
	title
	description
	thumbnail = MediaResource
	publisher
	created_year

GET world/worlds <- list worlds
POST world/worlds <- create new world
GET world/<worldid> <- static world view
PUT,PATCH,DELETE world/<worldid> <- modify world

Article
	id # is slug
	type = Choice
	world = Ref
	creator = Ref
	title = String
	description = String #short summary description
	content = String
	created_date = DateTime
	thumbnail = MediaResource
	status = # publishing status
	relations = ListField (
		relation_type = Choice
		article = Ref()

	PlaceData
		coordinate
		location_type

	PersonData
		born = Int
		died = Int
		gender = Choice
		occupation

	FractionData

	EventData
		from_date = 
		to_date = 

	CampaignData
		rule_system = String
		episodes = Tree
			id
			title =
			synopsis =
			content = List(Articles)
			epsiodes =

	ChronicleArticle

	ImageData
		media_resource = MediaResource

MediaResource
		mime_type
		file = File
		dimensions		

CampaignInstance
	campaignArticle = Ref
	group = Ref
	sessions [
		play_start = DateTime
		play_end = DateTime
		location
		description
		episodes = List(Episode)
		present_members = List(User)
	]
	chronicles = List(ChronicleArticle)

Typical access:
1) Fetch Article complete content with metadata and relations
2) Fetch article title, description and thumbnail only
3) Fetch article titles eligible for choice (similar to 2)
4) Fetch campaign with all scenes and summaries of relating articles

GET world/<worldid>/articles <- list articles
POST world/<worldid>/articles <- create new article
GET world/<worldid>/<articleid> <- static article view
PUT,PATCH,DELETE world/<worldid>/<articleid> <- edit article

Conversation
	participants
	title

Message
	content = String
	conversation = Ref
	user = Ref
	pub_date = DateTime

1) Fetch messages in converstation up to x days old
2) Fetch all messages from person

Group
	name
	location
	thumbnail
	masters = User[] ref
	members = User[] ref
	invitees = User[] ref

1) Fetch group with all members to add and remove
2) Fetch list of groups a person is member of

User
	username
	email
	password
	realname
	location
	thumbnail
	description
	xp
	join_date
	actions
	status

1) Fetch user profile
2) Fetch list of users


Above define the acceptable resources in raconteur. All of above will be requested through a REST-like interface. The REST interface and URL rules should be the same between fetching a page for viewing, and fetching JSON for machine reading. Some principles:
- Use the standard verbs; GET, POST, PUT, PATCH, DELETE
- For basic HTTP browsers that don't support all verbs, also accept POST, with the param ?method=PUT, PATCH, etc and interpret it as above
- The response can be full HTML (no param), partial HTML (?format=partial) and JSON (?format=json). Full HTML is a complete website with headers, etc. Partial HTML is only the affected "snippet" intended to be inserted somewhere. JSON is the raw format for machine reading.
- Use correct HTTP status codes. Error codes should come with a response explaining the error, in the same format as was requesteded
- For all GETs, the returned HTML can either be of a static representation, or a form. It can be decided by the view which will be returned (e.g. a static if no write access for current user) but appending /edit will always try to load the editable form version.
- When viewing list views, it should always be possible with the following operations:
-- filter: ?<field>=value . Will filter responses to only match having those values. If it cannot filter on this, respond with a 400 Bad Request with information
-- sort: ?sort=-<field>,<field>
-- search: ?q=value

Visual components
- Article (a text focused view). Only for single resource views.
- Widget (a small representation for a popup, modal, etc for single resource view. Used by Gallery.)
- Row (a row representation of a single resource. Used by Table.)
- Table (a sortable table with rows). Only for list resource views.
- Gallery (a stacked set of boxes). Only for list resource views.

										?render=page;json;in_table;in_page;in_box

GET		Resources/						?render=...
										?order_by=<field>;-<field>
										?<field>=x;<field__gt>=y;
										?do=view;edit;new;	
POST	Resources/						?render=...
GET		(Resources/)<SingleResource>/	?render=...
										?<field>=x;
										?do=view;edit;new;
POST	(Resources/)<SingleResource>/	?render=...
										?method=PUT;PATCH;DELETE
PUT		(Resources/)<SingleResource>/	?render=...
PATCH	(Resources/)<SingleResource>/	?render=...
DELETE	(Resources/)<SingleResource>/	?render=...


Responses
200		Rendered output as per argument
400		Bad request (general error or incorrect validation)
	If on HTML, we can just highlight the errors on the page
404		Not found (given resource id does not exist)
401		Unauthorized (not logged in or not access to article)
	If on HTML and not logged in, send to login page first
403		Forbidden (operation is not allowed)
500		Internal Server Error (python exception)

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


Template structure

page.html
	section.html
		model.html


model_form
	if partial then extend partial else extend "world.html"
	block: in_page
	block: in_table
	block: in_box
model_view
	extend page, table, box
	block: content
	block: in_table
	block: in_box
model_list
model_custom


Working with Forms

The form library is seemingly simple but infinitly complex when you scratch the surface. First, here are the components:

WTForms (package 'wtforms') - a generic library for building Form objects that can parse and validate data before filling up the real model object with it.

Flask-WTF (package 'flask.ext.wtf') - a mini library that joins the WTForms with Flask, such as automatically adding CSRF tokens (security)

Flask-Mongoengine (package 'flask.ext.mongoengine.wtf') - Comes with the automatic translation of Mongoengine Document objects (Model objects) into Forms by calling model_form() function, and also makes it easy to enhance an app with the Mongoengine layer.

Mongoengine (package ..) - Used by Flask-Mongoengine but does the real work. 

This is the lifecycle steps:

1) Create Model class (db.Documents)

2) Create Form class by telling model_form to parse all fields in Model class, and pick suitable HTML form fields that match each variable.

3) When you have a request for a form, instantiate the Form class for that model, and by calling each field of the form, render the HTML. If the Form was instantiated with a model object, the form will be pre-filled with real model data.

4) When you get a form post response back, let the form self-parse the request data, and then if it validates, tell the form to populate a Model object with the new data (overwriting any old data).

Issues:
EmbeddedDocuments in a Model is mapped as a FormField, which is a sub-form that pretends to be a field. So you get a recursive type of behaviour. Some of the problems:

Issue: CSRF tokens are automatically added by flask-mongoengine using the Form class from flask-wtf. This means also sub-forms get their own CSRF which seems exxagerated.
Solution: We can give model_form a different ModelConverter class, which contains the functions that map a Model field to a Form field. Here we can have a subclass that changes the behaviour of the function that creates FormFields (sub forms) from EmbeddedDocuments, to avoid using the CSRF enabled form here.

Issue: FormFields expect to have objects (EmbeddedDocument) to fill with data, but in some Model cases we may accept having "None" for some of the Embedded Documents. This means populate_obj() method will throw errors, because there is no object to populate, and the form doesn't know how to create a new one just because it got form data.
Solution: Articles have multiple EmbeddedFields, that may or may not be filled with data. Actually, among them, only one should be filled with data at the same time.
A) We could make sure the default value is always an empty object rather than None. This would make FormField behave well when trying to populate, even if populating with empty fields. But it would inflate the database uneccesarily and it would make it less easy to check if there is data to display (e.g. cannot just check for None on the EmbeddedDocumentField).
B) We could keep them as None by default, but it means, when someone creates an article we need to be able to instantiate the EmbeddedDocument (as the form can't do it), and when the type is changed, we need to None the old reference and insantiate the new. This step would have to happen AFTER validation but before populate_obj. Because we don't have "manual" access to the steps between validation and populate_obj, this cannot be done in current architecture.
C) We can change the FormField class (inherit) so that it's populate_obj method correctly sets only the active type's EmbeddedDocument fields to a new instance and sets all others to None.


 class ResourceHandler():
	dispatch_request(kwargs)
		resource = parse_id(kwargs)
		parents = self.parent.parse_parents(kwargs)
		if GET 
			r = self.get(resource=resource, parents=parents)
		else
		render(r)

class MessageHandler(ResourceHandler):

	# General INPUT to all handlers
	# parsed_args (filter, order_by, etc), {resourceA: instance, resourceB: instance}, op (normally implicit)
	# General OUTPUT from all handlers
	# template,  {resourceA: instance, resourceB: instance},  {resource_formA: form, resource_formB: form}, op, next
	
	# prefixes all parent urls before
	parent = Conversationhandler

	# default GET resource/<id>
	def get(kwargs)
		return {template:.., resource:.., resource_form:.., error:..., next:...}

	# default resource/resources
	def list(kwargs)
		return error(405) # Example for not allowed op

	# default POST resource/resources or GET resource/resources?op=post
	def post(kwargs)

	# default PATCH resource/<id> or POST resource/<id>?op=patch or GET resource/<id>?op=patch
	def patch(kwargs)

	# default PUT resource/<id> or POST resource/<id>?op=put or GET resource/<id>?op=put
	def put(kwargs)

	# default DELETE resource/<id> or POST resource/<id>?op=delete or GET resource/<id>?op=delete
	def delete(kwargs)

	@route('/backwards/', methods=['GET', 'POST'])
	def backwards()
		self.list(order_by='-'')

msgHandler = MessageHandler(...)



-------
FORUM DESIGN

Forum
- Board
-- Topic
--- Post (message)


Conversation

A conversation is a list of messages from users. The list will always be flat (not threaded) and ordered by time. A conversation can be eternal, but normally is started and held active within a certain time. A conversation has members. Members are allowed to post messages to that conversation. The conversation can be tied to different things. It can be a comment, where it is tied to a place in an article (or by default, at the bottom/top). Conversations can be grouped into topics.

Use of conversations
- Closed chats for a game session (all can write)
- Closed chat within a group, outside of game session (e.g. a permanent discussion)
- Public posting of messages (one writes, rest reads)
- Public discussion

'''
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
'''

Responses
200		Rendered output as per argument
400		Bad request (general error or incorrect validation)
	If on HTML, we can just highlight the errors on the page
404		Not found (given resource id does not exist)
401		Unauthorized (not logged in or not access to article)
	If on HTML and not logged in, send to login page first
403		Forbidden (operation is not allowed)
500		Internal Server Error (python exception)

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

If request full html:
	400		-> bad request
			if a edit/new of form, return original form with validation errors highlighted in requsted form and flash message shown
			if error with URL args, just flash message
	401		-> Unauthorized, redirect to login-page if not logged in, else flash message not allowed
	403		-> forbidden operation, just flash message that not possible with current user
	404		-> not found page
	500		-> flash message about internal server error
			if debug, go to debug instead

If request fragment:
	400		-> bad request
			if a validation error, return fragment html of complete form with validation errors
			else return text line to insert into flash
	401		-> return flash message that "need to be logged in (with a link to click?)"
	403		-> forbidden, return flash message that not possible
	404		-> return flash message
	500		-> return flash message

If request json:
	400		-> bad request
			if validation error, return json representation of form.errors
			else return normal json error dict
	401		-> unauthorized, return json error dict
	403		-> forbidden, return json error dict
	404		-> not found, return json error dict
	500		-> return json error dict


## Authorization system

The authorization system is there to limit access on the Raconteur system. It's represented
in a few ways:
- Limiting access to OPerations / URLs and throwing a 401 error
- Conditionally displaying links / html fragments only if the user is authorized to see it

Resource.py defines 8 standard operations on a resource, and they can all be generally classified
as read or write operations. A certain resource can be readable by everyone or only specific groups,
as well as writable. The exact logic for deciding authentication this depends on the resource.

The key to this is the function ResourceStrategy.allowed(op, instance)
op is the current operation being tested
instance refers to the specific instance of a resource, as most ops act on an instance.
If the op does not act on instances (e.g. list, new), it is not needed.
The user is automatically read from the flask.g object that keeps the current session.
allowed() will automaticalyl throw a ResourceError if the user is not allowed.

For templates, there is the macro called IS_ALLOWED() which works in a very similar way
but doesn't throw exceptions and instead just outputs what's inside the macro if allowed,
otherwise not.

Access to resources are normally given to groups. A group is a list of users, where 
there are "members" and "masters". By default, members will have read access, masters
have write access, and non-members no access.
Each resource has a special "group" which is the creator group, which normally means
the user who created the resource, if this is a field existing in the resource. 

Some access:
User. Read by all (if system-activated), write by user or admin.
Group. Read by all, write by group master or admin.
ImageAsset. Read by all, write by creator or admin.
Article. Read by those in Readgroup, Write by those in write groups.
World. Read by all, write by world creator group or admin.

### Domains and URLS
Fablr runs on fablr.co as host.
Blueprints point to a path of /blueprint/, e.g. fablr.co/blueprint, for example 
fablr.co/social
Static assets are served from either fablr.co/static or from asset.fablr.co. Asset
allows us to use several subdomains to allow parallell download.

Worlds are special cases, as they may want to stand on their own. A world is found
at <world>.fablr.co.
Some world publishers may have purchased their own domains. As such, they may want to
point publisherdomain.com to publisherdomain.fablr.co and they may even have other
worlds pointing to sub.publisherdomain.com.

The only place host matters is to match the URL route to a correct endpoint, and
when creating URLs using url_for.
When we use <world>.fablr.co it's important that fablr.co/world redirects to world.fablr.co
Also, when we use a publisherdomain, it's important that world.fablr.co still exists and
redirects to publisherdomain.

Logic:
@app.route('/', hostname=<worldslug>)
@app.route('/<worldslug>', hostname=<worldslug>)
