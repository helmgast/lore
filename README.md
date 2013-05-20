# RACONTEUR
Raconteur is a platform for sharing stories and fictional worlds. It's a wiki and a tool for gaming and for getting together with friends.

# DESIGN
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
* GET <id>/?partial or ?partial=True means server should only return partial HTML, ready to be inlined on calling page
* GET <id>/?json or ?json=True means server should only return JSON representation
* GET <id>/?arg=1&arg=2 means if we are getting a form, prefill these values (parsed as if it was a form POST)
* GET <id>/?form=xxx means that we are requesting a specific type of form, as most models can be represented by several.

###POST
* POST .../?partial or ?partial=True means we are posting from an inline form, and redirect destination should also be partial

###Errors
If there is an error with a GET or POST, it should return error information using the flash() system. If the request was partial, it should return a partial. Else, it should return to the page it came from or other page defined. This only includes errors that are not of HTTP nature, e.g. internal ones.

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
- Inline forms can come as smaller popups (if they are the same size as full form, one may as well call edit/?partial) or as parts of other forms. They can be loaded dynamically into pages or modals. They will not come with their own form and submit buttons, so need to be placed in a container classed .m_instance, so that we can use jQuery to figure out when to post parts of a form.
- Row forms are assumed to exist within a table, or more generally speaking, a list of instances. The form could still work as normal, which means the user can edit the (exposed) fields of the instance, like an Excel-sheet. The top container of the form representing a unique instance should have the class *.m_instance*. As we cannot rely on normal form logic (it would post the whole page) we must use jQuery to post the contents of this form, and this has to be triggered from a submit event that either comes from the form itself (embedded save button) or that comes from a parent container (e.g. a save button in the top of the table). However, commonly the row form can be accessed as /view, which means it's static. However, it can still be part of operations, or rather the list can have operations: add and remove. Add should fetch a new row and append it as well as creating a relationship model instance, remove should take away the row and delete the corresponding relationship. The adding (visually) and the adding (technically, with POST) may happen at different times.
- In-place editing. As we use the same template behind for both view and edit, it's fully possible to switch between them and load the contents using ?partial, no matter which form above it is. It's just a matter of changing /view to /edit and vice versa.

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


###MODEL VIEW HTML STRUCTURE
So a Model View is a dynamic view of model instances. It can be a single instance, or a collection of them (e.g. list). 
```
.m_view
    .m_instance // descendant of m_view, shows an instance of the model (e.g. a row in a table)
        .m_field/ descendant of m_instance, holds a particular field of the instance. Can also be a collection.
        .m_collection // if a view is instance an instance, it is a sub-view, e.g. of items in a collection field.
                // actions here work on the inner view, and does not know about the enclosing larger view
                // in sub-views, it is normally not legal to do new or delete. E.g. if a user has two groups, 
                // our intention is not normally to create or delete a group but instead to add or remove it from the user
            .m_instance //
                .m_action   // if we are inside an instance, add or remove will either completely remove the instance tag or add
                            // a new instance tag
            .m_selection
                .m_action   // if we are inside a selection, add or remove will select and deselect the instance in place, instead
                            // of removing/adding it
            .m_action
        .m_selector // a selector is different from a view, in that when we add and remove items, we simply select or deselect
                    // which means to leave the item in place but change it's rendering
    .m_action // descendant of m_view, button or a that invokes an action on the whole view, normally "add" or custom actions

<div .m_list>
    <div .m_instance #id>
        <div .m_field .m_[name]>value</div>
        OR
        <div .m_field .m_[name] data-value=value>Text</div>
        OR
        <div .m_list .m_[name]>
            <div .m_instance #id></div>
        </div>

        <div .m_actions>
            <a .m_action></a>
            <a .m_action></a>
        </div>
    </div>
</div>

<div .m_list .m_list_users>
    <div .m_instance .m_instance_users #m_marco>
        <div .m_field .m_field-username data-value=marco>[...thumbnailetc...]</div>
        <div .m_field .m_field-realname>Marco B</div>
        <div .m_field .m_field-location>Location</div>
        <div .m_actions>
            <a .m_action .m_action-follow href=/follow></a>
            <a .m_action .dropdown .m_action-changegroup>
                <ul .m_collection #m_masteredgroups>
                <li>
            </a>
            <a .m_action .m_action-sendmessage href=/conversation></a>
        </div>
    </div>
    <div .m_action></div>
</div>
```
Questions
- How to edit in place? How to edit when only parts of the fields are visible?
- How to deal with multiple selects? Both "selected" and "available". Selected is the many-to-many field of an instance. Available is a "collection".
- How to deal with actions that changes state on themselves?

##Instance-templates
A page shows views of models. A view is a representation of 1 to n instances of a model, e.g. "User".
The view is a HTML node in itself. All instances are children (not direct?) of the model view.
Fields of the model instance is children nodes of the instance.
So, a table can be the model view, the instance each row and the field each cell.
A model view or instance does not have to show all available instances or fields of that model.
There may be a subset. Some fields may also be additional, e.g. there can be pure presentation nodes in between.
This means that the HTML representation of a field or instance should be enough to at least identify it, if not to carry all information known about it.

Each instance represents an ID on the server. This is given by the class .m_id-xxx . It has to be a class because
there may be multiple representations of the same instance on the same page (and the id attribute has to be unique).

A model instance can also contain action links. An action is a A or BUTTON that is a child of the model view.
The model view will always deal with the action, but some are defined on a per instance basis, some are defined in the view.

This is defined in the view:
/new    If not in new mode, this will show the form for a new instance. If in new mode, and the POST is successful, it will add the new
        instance as the last child to the view. If failed, it will display a message, and go back to inactive mode.

This is defined per instance.
/edit   If not in edit mode, this will swap the sending instance to a form (replace divs with inputs, etc). If in edit mode, this will
        instead stop edit mode and replace the instance with the new information, if the POST was successful, or revert, if it failed.
/remove If not in remove mode, activate it by showing a prompt. If in remove mode, and the POST was successful, it will remove the instance from the view.

An action corresponds (and is identified by) the keyword at the end of its URL, given by HREF. This means that you can always fall back on going to the link to take the action.

When changes are made to an instance as above, it may also be necessary to propagate those changes. Every other instance with same ID, or model view with 
same ID, will be updated as well. (consider doing this lazily, e.g. only load the new instance if the view is shown).

A model can also have custom actions. These also correspond to a URL for GET and POST. For example, "send message", "follow", etc. Usually these actions
relate to what the current user can do with them. Custom actions will need to be defined to be handled on a per model view class basis.

###Type of action presentations:
One-click   If the actions needs no prompt nor user input, this button simply executes a POST to action URL and changes presentation accordingly.
In-place    This all fields of an instance node into input fields in a form. This requires user input.
Modal       This will launch a modal that essentially contains a form. This is for prompts or edits that cannot be made in place, or when we need to get             the form from the server.

###What is common between actions is this:
- They are a A or BUTTON element with a href
- When clicked/activated, they will trigger an event
- The event will be caught by the encompassing model view
- The model view will use the calling element, it's attributes and sometimes it children nodes as the input information needed.
- The action will be in the following states. Inactive -> Activated ->(POST)-> Success -> (GET) -> (change presentation) -> Inactive
- An action can in some cases skip the inactive state, for example if it is a

###Server vs client role
The server will decide which actions are available and what filter or fields are shown. The client can not add or change this. It can only do incremental changes to what was given by the server. This means, no authorization or access control is done on the client. The server will validate the POST of each action and either accept or deny it. It will also have to send back information to the client on what it ended up deciding. That means, it has to respond with the resource resulting from the POST. For example, a new, add or remove can be interpreted differently in the server or cause some other state change in the model that has to be updated.

###Collection fields
Most fields are single variable, e.g. a textstring or integer. But some are collection fields. This means that the field value is chosen as one or several items from a collection. Typical example is the multiselect component of a form. It can be groups that a user is member of, etc.
The selected value(s) is the value of the field. In a form, each selected value will be added to the POST data. (TODO - treat the available values as a model view, meaning it can change during use, e.g. add or remove available groups).

When we add or remove in collections as actions. In some cases, we may only want to show the selected items in the list. Sometimes we want to show all available, and simply select or deselect.