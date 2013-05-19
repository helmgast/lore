from flask import request, render_template, flash, redirect, url_for
from raconteur import auth

def generate_flash(action, name, model_identifiers, dest=''):
    s = '%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1 else '', ', '.join(model_identifiers), ' to %s' % dest if dest else '')
    flash(s, 'success')
    return s

def error_response(msg, level='error'):
    flash(msg, level)
    return render_template('includes/partial.html')

# A wrapper around the combination of a model instance, a form and an operation.
# Is instantiated per request.
# In templates it can be accessed by name 'resource' or by same name as the
# modelclass in lowercase, e.g. 'article'.
# The object exposes method field() to get a form field, falling back to just field value if no form
# To access the underlying model object, one has to call e.g. article.instance.<attribute>
class ResourceInstance:
    def __init__(self, op, form, instance):
        self.op = op # type of operation
        self.form = form # form class
        self.instance = instance # actual model object instance

    def op_is_new(self):
        return self.op == ResourceHandler.NEW

    def field(self, name, non_editable=False, **kwargs):
        if non_editable or not self.form: # just print the value
            return getattr(self.instance, name)
        else: # print the form
            return getattr(self.form, name)(**kwargs)

# A handler for resources that can be subclassed. Is instantiated only once
# and will then act as a factory for ResourceInstances per request.
class ResourceHandler:
    # four operations on model
    EDIT        = 1 # edit (view with form, and post to that form)
    VIEW        = 2 # view (view without form, e.g. static)
    NEW         = 3 # new (view form for new instance and post to that form)
    DELETE      = 4 # delete (remove instance)
    ops = {EDIT:'edit',VIEW:'view',NEW:'new',DELETE:'delete'}
    op_messages = {EDIT: 'edited', NEW: 'created', DELETE:'deleted'}

    def __init__(self, model_class, form_class, template, route):
        self.model_class = model_class
        self.form_class = form_class
        self.template = template
        self.route = route
        self.resource_name = model_class.__name__.lower().split('.')[-1] # class name, ignoring package name

    def get_resource_instance(self, op, user, instance=None): # to be overriden
        return ResourceInstance(op, self.form_class(obj=instance) if (op==self.EDIT or op==self.NEW) else None, instance)

    def get_redirect_url(self, instance):
        return url_for(self.route, id=instance.id)

    def prepare_get(self, op, user, instance=None): # to be overriden
        pass

    def after_post(self, op, user, instance=None): # to be overriden
        pass

    def allowed(self, op, user, instance=None): # to be overriden
        print "Warning: Allowed function called without being overriden"
        return False

    def handle_request(self, op, instance=None, redirect_url=None, **kwargs):
        if not instance and not op==self.NEW:
            raise TypeError("Cannot handle operation %s without instance" % op)
        # Boolean shorthands for if request is GET or POST
        GET, POST = (request.method == 'GET'), request.method == 'POST', 
        user = auth.get_logged_in_user()
        allowed = self.allowed(op, user, instance)
        if op==self.EDIT and not allowed and self.allowed(self.VIEW, user, instance):
            op = self.VIEW # revert to view if we can't edit but still allowed to view
        elif not allowed:
            return error_response("You are not allowed to %s %s" % (op, instance if instance else self.model_class))
        print "Doing a %s, %s on %s" % (request.method, self.ops[op], instance)
        if GET:
            if op==self.DELETE:
                print request.url
                return render_template('includes/confirm.html', url=request.base_url, #TODO, this will skip partial args, always intended? 
                    action=self.op_messages[op], instances={'instance':[instance]}, **kwargs)
            else:
                # Add our arguments to any incoming arguments, kwargs is argument dictionary
                kwargs['resource'] = self.get_resource_instance(op, user, instance) # as default make instance available named by 'resource'
                kwargs[self.resource_name] = kwargs['resource'] # also make instance available named by class
                kwargs['partial'] = True if request.args.has_key('partial') else None
                return render_template(self.template, **kwargs)
        elif POST:
            if op==self.EDIT or op==self.NEW:
                # Create form object based on request and existing instance
                self.form = self.form_class(request.form, obj=instance)
                if self.form.validate():
                    if op==self.NEW: # create an instance as we won't have one yet
                        instance = self.model_class()
                    self.form.populate_obj(instance)
                    print request.form
                    print instance.content
                    instance.save()
                    print instance
                    self.after_post(op, user, instance) # Run any subclassed operations to be done after post
                    flash("%s was successfully %s" % (instance, self.op_messages[op]), 'success')
                    user.log("%s %s" % (self.op_messages[op], instance))
                    redirect_url = redirect_url if redirect_url else self.get_redirect_url(instance)
                    print "Redirecting to %s" % redirect_url
                    return redirect(redirect_url)
                else:
                    return error_response("Input data %s to %s %s did not validate" % (request.form, self.ops[op], self.model_class))
            elif op==self.DELETE:
                s = "%s" % instance
                instance.delete_instance()
                flash("%s was successfully deleted" % s, 'success')
                user.log("deleted %s" % s)
                redirect_url = redirect_url if redirect_url else self.get_redirect_url(instance)
                print redirect_url
                return redirect(redirect_url)
        return "Error"