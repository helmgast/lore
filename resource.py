from flask import request, render_template, flash, redirect, url_for
from raconteur import auth
from wtfpeewee.orm import model_form
from flask.views import View
from flask_peewee.utils import get_object_or_404, object_list, slugify
from raconteur import the_app

def generate_flash(action, name, model_identifiers, dest=''):
    s = '%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1 else '', ', '.join(model_identifiers), ' to %s' % dest if dest else '')
    flash(s, 'success')
    return s

def error_response(msg, level='error'):
    flash(msg, level)
    return render_template('includes/inline.html')

# A wrapper around the combination of a model instance, a form and an operation.
# Is instantiated per request.
# In templates it can be accessed by name 'resource' or by same name as the
# modelclass in lowercase, e.g. 'article'.
# The object exposes method field() to get a form field, falling back to just field value if no form
# To access the underlying model object, one has to call e.g. article.instance.<attribute>
class ResourceRequest:
    def __init__(self, op, form, instance):
        self.op = op # type of operation
        self.form = form # form class
        self.instance = instance # actual model object instance
        self.model_obj = instance

    def op_is_new(self):
        return self.op == ResourceHandler.NEW

    def make_request(self, *args):
        return None

    def field(self, name, non_editable=False, **kwargs):
        if non_editable or not self.form: # just print the value
            return getattr(self.instance, name)
        else: # print the form
            return getattr(self.form, name)(**kwargs)

# WTForms Field constructor args
# label - The label of the field. Available after construction through the label property.
# validators - A sequence of validators to call when validate is called.
# filters - A sequence of filters which are run on input data by process.
# description - A description for the field, typically used for help text.
# id - An id to use for the field. A reasonable default is set by the form, and you shouldnt need to set this manually.
# default - the default value to assign to the field, if no form or object input is provided. May be a callable.
# widget - If provided, overrides the widget used to render the field.
# _form - The form holding this field. It is passed by the form itself during construction. You should never pass this value yourself.
# _name - The name of this field, passed by the enclosing form during its construction. You should never pass this value yourself.
# _prefix - The prefix to prepend to the form name of this field, passed by the enclosing form during construction.
# 
# Rendering args
# any html input
#
# set prefilled values: form(formdata,... ) <- put args into formdata
# fix(hide) certain fields: simply don't display them in the template?

# A handler for resources that can be subclassed. Is instantiated only once
# and will then act as a factory for ResourceRequests per request.
class ResourceHandler:
    # four operations on model
    EDIT        = 1 # edit (view with form, and post to that form)
    VIEW        = 2 # view (view without form, e.g. static)
    NEW         = 3 # new (view form for new instance and post to that form)
    DELETE      = 4 # delete (remove instance)
    ops = {EDIT:'edit',VIEW:'view',NEW:'new',DELETE:'delete'}
    op_messages = {EDIT: 'edited', NEW: 'created', DELETE:'deleted'}

    def __init__(self, model_class, form_class, template, route):
        self.resource_name = model_class.__name__.lower().split('.')[-1] # class name, ignoring package name
        self.model_class = model_class
        self.form_class = form_class
        self.template = template if template else 'models/%s.html' % self.resource_name
        self.route = route

    def get_resource_request(self, op, user, instance=None): # to be overriden
        return ResourceRequest(op, self.form_class(obj=instance) if (op==self.EDIT or op==self.NEW) else None, instance)

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
                kwargs['resource'] = self.get_resource_request(op, user, instance) # as default make instance available named by 'resource'
                kwargs[self.resource_name] = kwargs['resource'] # also make instance available named by class
                kwargs['inline'] = True if request.args.has_key('inline') else None
                return render_template(self.template, **kwargs)
        elif POST:
            if op==self.EDIT or op==self.NEW:
                # Create form object based on request and existing instance
                self.form = self.form_class(request.form, obj=instance)
                print "In OLD resource %s %s %s" % (request.form, instance, self.form_class)

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

# Article, contains: world, article, article.type, article.relations
# article.form, article.type.form, article.relations.form
# form['article'], form['articletype'], form['relation']
# article_form, articletype_form, relation_form
# action_url['article'], action_url['articletype']

# Redirect URL pattern
# [GET, POST] article/new -> article/<news>/view (url_for(.article, article_slug=news))
# [GET] article/list
# [GET,POST] article/<s>/edit -> article/<s>/view
# [GET] article/<s>/view
# [GET, POST] article/<s>/delete -> article/

class ModelRequest(View):
    methods = ['GET']
    def __init__(self, server, op):
        self.server = server
        self.op = op
        self.model_obj = None # make sure it exists in object
        self.form = None # make sure it exists in object

    ## Gives us shortcut from template to access model_obj fields
    def __getattr__(self, name):
        if self.model_obj and hasattr(self.model_obj, name):
            return getattr(self.model_obj, name)
        else:
            raise AttributeError("No %s attribute in model_obj" % name)

    def get_obj(self, identifier):
        if self.server.identifier == 'slug':
            return get_object_or_404(self.server.model_class, self.server.model_class.slug == identifier)
        else:
            return get_object_or_404(self.server.model_class, self.server.model_class.id == identifier)

    def get_url(self, op, verbose, **identifiers):
        # Return an url for this Model class, given op, a model_obj (or identifier) and any parents.
        # If no parents given, assume direct.
        # should assume added operations
        if self.identifiers:
            identifiers.update(self.identifiers)
        if self.server.model_name not in identifiers:
            identifiers[self.server.model_identifier] = self.model_obj.identifier # if no identifier was given we can attempt to add it

        # Make endpoint according to server rules. Assume instance if we get current model_identifier in identifiers
        return url_for('.%s_%s' % (op, self.server.model_name), **identifiers)

    def allowed(self, op, user, model_obj=None): # to be overriden
        if op in ['list','view']:
            return True
        else:
            print "According to default ModelServer, all state changing operations disallowed! Override method to change!"
            return True ## TODO false

    def make_request(self, op, model_name, model_obj=None, form_args={}):
        server = ModelServer.servers[model_name]
        if op not in server.ops_by_identifier:
            raise ValueError("Op %s is not defined in this servers available options by identifier" % op)
        if not model_obj:
            op = 'new' # if no value was given, we must be creating a new
        mr = server.model_request_class(server, op)
        mr.model_obj = model_obj
        if not mr.allowed(op, auth.get_logged_in_user(), model_obj):
            return None
        mr.prepare_form(form_args)
        return mr

    def prepare_form(self, form_args={}):
        if self.op=='edit' or self.op=='new':
            self.form = self.server.form_class(obj=self.model_obj)

    def dispatch_request(self, **identifiers):
        self.identifiers = identifiers
        if not self.op:
            if identifiers[self.server.model_identifier]: # no op, but we have identifier -> 'view'
                self.op = 'view'
            else:
                self.op = 'list'
        if self.op not in self.server.ops_by_identifier and self.op not in self.server.ops_by_model:
            error_response("Operation %s not valid!" % self.op) # TODO make it into proper 404?
        
        ## Convert identifiers into model_objs
        if self.op in self.server.ops_by_identifier:
            # complete construction of this modelrequest (model_obj, form, etc)
            self.model_obj = self.get_obj(identifiers[self.server.model_identifier])

        ## Is user allowed?
        user = auth.get_logged_in_user()
        allowed = self.allowed(self.op, user, self.model_obj)
        if not allowed:
            return error_response("You are not allowed to %s %s" % (self.op, self.model_obj if self.model_obj else self.server.model_class))

        if request.method == 'GET':
            
            ## Prepare forms and render view or form
            self.prepare_form()

            ## Prepare render_args
            render_args = {self.server.model_name:self} # add this request
            if request.args.has_key('inline'):
                render_args['inline'] = True
                render_args['template_parent'] = 'includes/inline.html'
            elif request.args.has_key('row'):
                render_args['row'] = True
                render_args['template_parent'] = 'includes/row.html'

            # Include adding parents to modelrequests
            for k in identifiers.keys(): # remaining identifiers will be parent identifiers
                if k != self.server.model_identifier and k in ModelServer.servers:
                    print "Making new ModelRequest for %s" % k
                    # TODO this is a hack, we prob only need model_obj, but can only create by first making dummy model_request
                    mr = ModelServer.servers[k].model_request_class(ModelServer.servers[k], 'view')
                    mr.model_obj = mr.get_obj(identifiers[k]) 
                    render_args[ModelServer.servers[k].model_name] = mr

            if self.op=='delete':
                return render_template('includes/confirm.html', url=request.base_url, #TODO, this will skip partial args, always intended? 
                    action=self.server.op_messages[self.op], model_objs={'model_obj':[self.model_obj]}, **render_args)
            else:
                #print encode(self.form.world, 'utf-8')
                return render_template(self.server.templates[self.op], **render_args)

        elif request.method == 'POST':

            ## Handle incoming data and commit to model
            if self.op=='edit' or self.op=='new':
                # Create form object based on request and existing model_obj
                self.form = self.server.form_class(request.form, obj=self.model_obj)
                print "In NEW resource %s %s %s" % (request.form, self.model_obj, self.server.form_class)
                if self.form.validate():
                    if self.op=='new': # create an model_obj as we won't have one yet
                        self.model_obj = self.server.model_class()
                    self.form.populate_obj(self.model_obj)
                    self.model_obj.save()
                    print "Now identifiers are %s" % identifiers
                    identifiers[self.server.model_identifier]=getattr(self.model_obj,identifier) # for redirect URL, we will send to new identifier (if changed or new obj)
                    flash("%s was successfully %s" % (self.model_obj, self.server.op_messages[self.op]), 'success')
                    user.log("%s %s" % (self.server.op_messages[self.op], self.model_obj))
                    return redirect(self.get_url('view',identifiers))
                else:
                    return error_response("Input data %s to %s %s did not validate" % (request.form, self.op, self.server.model_class))
            elif self.op=='delete':
                s = "%s" % self.model_obj
                self.model_obj.delete_model_obj()
                flash("%s was successfully deleted" % s, 'success')
                user.log("deleted %s" % s)
                return redirect(self.get_url('list',identifiers))

class ModelServer:
    servers = {} # class global variable to remember all servers created
    op_messages = {'edit': 'edited', 'new': 'created', 'delete':'deleted'}

    @staticmethod
    def get_model_name(model_class):
        return model_class.__name__.lower().split('.')[-1] # class name, ignoring package name

    def __init__(self, app, model_class, templates={}, parent=None, form_class=None, model_request_class=None): # should allow override formclass, template, route
        self.app = app
        self.endpoints = {}
        self.model_class = model_class
        self.model_name = ModelServer.get_model_name(model_class)
        if 'slug' in self.model_class.__dict__:
            self.identifier = 'slug'
        else:
            self.identifier = 'id'
        self.model_identifier = '%s_%s' % (self.model_name, self.identifier)
        self.model_request_class = model_request_class if model_request_class else ModelRequest
        if not form_class:
            self.form_class = model_form(model_class) # Generate form based on model
        else:
            self.form_class = form_class
        self.parent = parent
        self.templates = {
            'list': 'models/%s_list.html' % self.model_name,
            'new': 'models/%s_view.html' % self.model_name,
            'view': 'models/%s_view.html' % self.model_name,
            'edit': 'models/%s_view.html' % self.model_name,
            'delete': 'includes/confirm.html',
        }
        self.ops_by_model = ['list','new']
        self.ops_by_identifier = ['view','edit','delete']
        self.templates.update(templates) # overwrite with any given parameters

        self.add_op('list', self.model_request_class, verbose=True, on_instance=False)
        self.add_op('new', self.model_request_class, verbose=True, on_instance=False, methods=['GET','POST'])
        self.add_op('view', self.model_request_class, verbose=True, on_instance=True)
        self.add_op('edit', self.model_request_class, verbose=True, on_instance=True, methods=['GET','POST'])
        self.add_op('delete', self.model_request_class, verbose=True, on_instance=True, methods=['GET','POST'])

        ModelServer.servers[self.model_name] = self
        ModelServer.servers[self.model_identifier] = self # also findable by identifier

    def add_op(self, op, mr_class, verbose=True, on_instance=True, methods=['GET']):
        # direct -> models/model/ + op and models/model/ + <slug>/ + op (model_direct, model_direct_on_instance)
        # verbose -> parent/parent/ + model/ + op and parent/parent/ + <slug>/ + op (model_verbose, model_verbose_on_instance)
        if verbose:
            parent_identifiers = self.get_parent_identifiers()
            route = '/%s' % (''.join(['<%s>/'%s for s in parent_identifiers]) if parent_identifiers else '')
        else:
            route = '/models/%s/' % self.model_name
        if on_instance:
            route += '<%s>/' % self.model_identifier
        elif verbose:
            route += '%s/' % self.model_name
        # elif verbose: # small exception to rule, that in verbose mode, not on_instance, we need to add model_name
        #     route += '%s/' % self.model_name
        route += op
        endpoint = '%s_%s' % (op, self.model_name)
        print "Added url %s, with endpoint %s handled by %s" % (route, endpoint, mr_class.__name__)
        mr_class.methods = methods # TODO hack, we are setting the methods on the class before calling as_view, to register POST and other
        self.app.add_url_rule(route, view_func=mr_class.as_view(endpoint, self, op))

    def get_parent_identifiers(self):
        identifiers = []
        if self.parent:
            identifiers += self.parent.get_parent_identifiers()+[self.parent.model_identifier]
        return identifiers