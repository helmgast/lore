# Design

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

	PlaceArticle
		coordinate
		location_type

	PersonArticle
		born = Int
		died = Int
		gender = Choice
		occupation

	FractionArticle

	EventArticle
		from_date = 
		to_date = 

	CampaignArticle
		rule_system = String
		episodes = Tree
			id
			title =
			synopsis =
			content = List(Articles)
			epsiodes =

	ChronicleArticle

	ImageArticle
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
404		Not found (given resource id does not exist)
401		Unauthorized (not logged in or not access to article)
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