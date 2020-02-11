# Forms

The form library is seemingly simple but infinitly complex when you scratch the surface. First, here are the components:

- WTForms (package `wtforms`) - a generic library for building Form objects that can parse and validate data before filling up the real model object with it.
- Flask-WTF (package `flask.ext.wtf`) - a mini library that joins the WTForms with Flask, such as automatically adding CSRF tokens (security)
- Flask-Mongoengine (package `flask.ext.mongoengine.wtf`) - Comes with the automatic translation of Mongoengine Document objects (Model objects) into Forms by calling model_form() function, and also makes it easy to enhance an app with the Mongoengine layer.
- Mongoengine (package `mongoengine`) - Used by Flask-Mongoengine but does the real work.

This is the lifecycle steps:

1. Create Model class (Document)
2. Create Form class by telling model_form to parse all fields in Model class, and pick suitable HTML form fields that match each variable.
3. When you have a request for a form, instantiate the Form class for that model, and by calling each field of the form, render the HTML. If the Form was instantiated with a model object, the form will be pre-filled with real model data.
4. When you get a form post response back, let the form self-parse the request data, and then if it validates, tell the form to populate a Model object with the new data (overwriting any old data).

## Managing form data

Each field at the time of submission of a form can be:

- Fully writable (any data in the form, if valid, will be set as new model value). This is default WTForm behavior.
- Pre-filled and writable (a variant of above, but we pre-fill with suggested data)
- Not writable (the field is visible, but set to "disabled". Any incoming formdata for this field has to be ignored)
- Excluded (the field is not in the HTML form, any incoming data has to be ignored.)
  This is not a static setting for the field. In one context, a field may be writable but in another not. For example, only an admin may be able to change certain fields, or they may only be editable if they haven't been given a value before.

Available WTForm API:

- `Form(formdata, obj, data, **kwargs)`. formdata is the data in a POST request. obj is an existing model object. data is a dict, and kwargs is additional arguments. They will not merge, e.g. they will only be applied if the previous left-wise argument was empty. So if formdata is provided, none of the other args will apply.

## Issues

EmbeddedDocuments in a Model is mapped as a FormField, which is a sub-form that pretends to be a field. So you get a recursive type of behaviour. Some of the problems:

**Issue**: CSRF tokens are automatically added by flask-mongoengine using the Form class from flask-wtf. This means also sub-forms get their own CSRF which is incorrect.
Solution: We can give model_form a different ModelConverter class, which contains the functions that map a Model field to a Form field. Here we can have a subclass that changes the behaviour of the function that creates FormFields (sub forms) from EmbeddedDocuments, to avoid using the CSRF enabled form here.

**Issue**: FormFields expect to have objects (EmbeddedDocument) to fill with data, but in some Model cases we may accept having "None" for some of the Embedded Documents. This is especially true when a model has an option of containing one of several types of Embedded Documents, but normally only one contains a reference and the others are None. This means `populate_obj()` method will throw errors, because there is no object to populate, and the form doesn't know how to create a new one just because it got form data.
Solution: Articles have multiple EmbeddedFields, that may or may not be filled with data. Actually, among them, only one should be filled with data at the same time.

A) We could make sure the default value is always an empty object rather than None. This would make FormField behave well when trying to populate, even if populating with empty fields. But it would inflate the database uneccesarily and it would make it less easy to check if there is data to display (e.g. cannot just check for None on the EmbeddedDocumentField).

B) We could keep them as None by default, but it means, when someone creates an article we need to be able to instantiate the EmbeddedDocument (as the form can't do it), and when the type is changed, we need to None the old reference and instantiate the new. This step would have to happen AFTER validation but before `populate_obj`. Because we don't have "manual" access to the steps between validation and `populate_obj`, this cannot be done in current architecture.

C) We can change the FormField class (inherit) so that it's `populate_obj` method correctly sets only the active type's EmbeddedDocument fields to a new instance and sets all others to None.

## Example

Model Article consists of following fields:

- title (char)
- world (->model)
- content (text)
- type (choice)
- persontype (<-model) (an associated model)
- article relations (->\*models) (collection of relations)

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
- Row forms are assumed to exist within a table, or more generally speaking, a list of instances. The form could still work as normal, which means the user can edit the (exposed) fields of the instance, like an Excel-sheet. The top container of the form representing a unique instance should have the class _.m_instance_. As we cannot rely on normal form logic (it would post the whole page) we must use jQuery to post the contents of this form, and this has to be triggered from a submit event that either comes from the form itself (embedded save button) or that comes from a parent container (e.g. a save button in the top of the table). However, commonly the row form can be accessed as /view, which means it's static. However, it can still be part of operations, or rather the list can have operations: add and remove. Add should fetch a new row and append it as well as creating a relationship model instance, remove should take away the row and delete the corresponding relationship. The adding (visually) and the adding (technically, with POST) may happen at different times.
- In-place editing. As we use the same template behind for both view and edit, it's fully possible to switch between them and load the contents using ?inline, no matter which form above it is. It's just a matter of changing /view to /edit and vice versa.
