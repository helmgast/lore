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

	MediaArticle
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
	block: content
	block: in_table
	block: in_box
model_view
	extend page, table, box
	block: content
	block: in_table
	block: in_box
model_list
model_custom