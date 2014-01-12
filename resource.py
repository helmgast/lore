from flask import request, render_template, flash, redirect, url_for
from raconteur import auth
from flask.ext.mongoengine.wtf import model_form
from flask.views import View
from raconteur import the_app
from wtforms.compat import iteritems
from wtforms.fields import FormField

def generate_flash(action, name, model_identifiers, dest=''):
    s = u'%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1 else '', ', '.join(model_identifiers), u' to %s' % dest if dest else '')
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

class ResourceAccessStrategy:

    def __init__(self, model_class, plural_name, id_field='id', form_class=None, parent_strategy=None):
        self.form_class = form_class if form_class else model_form(model_class)
        self.model_class = model_class
        self.resource_name = model_class.__name__.lower().split('.')[-1] # class name, ignoring package name
        self.plural_name = plural_name
        self.parent = parent_strategy
        self.id_field = id_field
        print 'Strategy created for "' + self.resource_name + '"'

    def get_url_path(self, part, op=None):
        parent_url = ('' if (self.parent is None) else self.parent.url_item(None))
        op_val = ('' if (op is None) else ('/' + op))
        url = parent_url + '/' + part + op_val
        return url

    def url_list(self, op=None):
        return self.get_url_path(self.plural_name, op)

    def url_item(self, op=None):
        return self.get_url_path('<'+self.resource_name+'>', op)

    def item_template(self):
        return '%s_item.html' % self.resource_name

    def list_template(self):
        return '%s_list.html' % self.resource_name

    def fetch_item(self, **kwargs):
        id = kwargs[self.resource_name]
        return self.model_class.objects.get(**{self.id_field:id})

    def create_item(self):
        return self.model_class.create()

    def fetch_list(self, args):
        qr = self.model_class.objects()
        filters = {}
        for key in args.keys():
            if key == 'order_by':
                qr = qr.order_by(*args.getlist('order_by'))
            else:
                fieldname = key.split('__')[0] 
                print fieldname, (fieldname in self.model_class.__dict__)
                if fieldname[0] != '_' and fieldname in self.model_class.__dict__:
                    filters[key] = args.get(key)
        print filters
        if filters:
            qr = qr.filter(**filters)
        # TODO very little safety in above as all filters are allowed
        return qr

    def fetch_parents(self, **kwargs):
        if not self.parent:
            return {}
        # Silently pop arg, if existing, relating to current resource
        kwargs.pop(self.resource_name, None) 
        grandparents = self.parent.fetch_parents(**kwargs)
        grandparents[self.parent.resource_name] = self.parent.fetch_item(**kwargs)
        #print "all parents %s" % grandparents 
        return grandparents
      
    def endpoint_name(self, suffix):
        return self.resource_name + '_' + suffix

    def allowed(self, op, instance=None):
        parent_allowed = self.parent.allowed(op, instance) if self.parent else True
        # If instance exists, check allowed on that, otherwise check on model class
        return parent_allowed

    def allowed_any(self, op):
        return self.allowed(op, None);

    def allowed_on(self, op, instance):
        return self.allowed(op, instance);


class ResourceHandler2:

    def __init__(self, strategy):
        self.form_class = strategy.form_class
        self.strategy = strategy

    def register_urls(self, app):
        st = self.strategy
        app.add_url_rule(st.url_item(), methods=['GET'], view_func=self.get, endpoint=st.endpoint_name('get'))
        app.add_url_rule(st.url_item(), methods=['POST'], view_func=self.post, endpoint=st.endpoint_name('post'))
        app.add_url_rule(st.url_item(), methods=['PUT'], view_func=self.put, endpoint=st.endpoint_name('put'))
        app.add_url_rule(st.url_item(), methods=['PATCH'], view_func=self.patch, endpoint=st.endpoint_name('patch'))
        app.add_url_rule(st.url_item(), methods=['DELETE'], view_func=self.delete, endpoint=st.endpoint_name('delete'))
        app.add_url_rule(st.url_item('edit'), methods=['GET'], view_func=self.get_edit, endpoint=st.endpoint_name('get_edit'))
        app.add_url_rule(st.url_list(), methods=['GET'], view_func=self.get_list, endpoint=st.endpoint_name('get_list'))
        app.add_url_rule(st.url_list(), methods=['POST'], view_func=self.post_new, endpoint=st.endpoint_name('post_new'))
        app.add_url_rule(st.url_list('new'), methods=['GET'], view_func=self.get_new, endpoint=st.endpoint_name('get_new'))
        app.add_url_rule(st.url_list('edit'), methods=['GET'], view_func=self.get_edit_list, endpoint=st.endpoint_name('get_edit_list'))

    def render_list(self, list=None, parents=None, edit=False):
        render_args = {self.strategy.plural_name:list, 'edit':edit}
        render_args.update(parents)
        return render_template(self.strategy.list_template(), **render_args)
    
    def render_one(self, instance=None, parents=None, edit=False, new=False, form=None):
        render_args = {self.strategy.resource_name:instance, 'edit':edit}
        render_args[self.strategy.resource_name+'_form'] = form
        render_args.update(parents)
        return render_template(self.strategy.item_template(), **render_args)

    def get(self, **kwargs):
        instance = self.strategy.fetch_item(**kwargs)
        parents = self.strategy.fetch_parents(**kwargs)
        if not self.strategy.allowed_on('read', instance):
            return self.render_one(error=401)
        return self.render_one(instance, parents)

    def get_edit(self, **kwargs):
        instance = self.strategy.fetch_item(**kwargs)
        parents = self.strategy.fetch_parents(**kwargs)
        if not instance:
            return self.render_one(error=400)
        if not self.strategy.allowed_on('write', instance):
            return self.render_one(error=401)
        # TODO add prefil form functionality
        form = self.form_class(obj=instance)
        return self.render_one(edit=True, form=form)
    
    def get_new(self, *args, **kwargs):
        # no existing instance as we are creating new
        parents = self.strategy.fetch_parents(**kwargs)
        if not self.strategy.allowed_any('write'):
            return self.render_one(error=401)
        # TODO add prefil form functionality
        form = self.form_class(request.args, obj=None)
        return self.render_one(new=True, form=form)

    def get_list(self, *args, **kwargs):
        parents = self.strategy.fetch_parents(**kwargs)
        if not self.strategy.allowed_any('read'):
            return self.render_one(error=401)
        # list_args = self.get_list_args()
        # if not list_args:
        #     return self.render_one(error=400)
        list = self.strategy.fetch_list(request.args)
        # Filter on allowed instances?
        return self.render_list(list=list, parents=parents)

    def get_edit_list(self, *args, **kwargs):
        if not self.strategy.allowed_any('write'):
            return self.render_one(error=401)
          
        list_args = self.get_list_args()
        if not list_args:
            return self.render_one(error=400)    
        list = self.strategy.fetch_list(list_args)
        # Filter on allowed instances?
        return self.render_list(edit=True, instance=list)

    def post(self, *args, **kwargs):
        if request.args.has_key('method'):
            method = request.args.get('method')
            if method == 'PUT':
              return self.put(*args, **kwargs);
            elif method == 'PATCH':
              return self.patch(*args, **kwargs)
            elif method == 'DELETE':
              return self.delete(*args, **kwargs)
            else:
              return self.render_one(error=400); #error_response, invalid method
        else:
          return self.render_one(error=400, msg="Not REST operation"); #error_response, missing method

    def post_new(self, *args, **kwargs):
        if not self.strategy.allowed_any('write'):
            return self.render_one(error=401)
        form = self.form_class(request.form, obj=None)
        if not form.validate():
            return self.render_one(error=403)
        obj = self.strategy.create_item()
        form.populate_obj(obj)
        obj.save()
        return redirect()

    def put(self, *args, **kwargs):
        instance = self.strategy.fetch_item(id)
        if not instance:
            return self.render_one(error=400)
        if not self.strategy.allowed_on('write', instance):
            return self.render_one(error=401)
        form = self.form_class(request.form, obj=None)
        if not form.validate():
            return self.render_one(error=403)
        form.populate_obj(instance)
        instance.save()        
        return redirect()

    def patch(self, *args, **kwargs):
        instance = self.strategy.fetch_item(id)
        if not instance:
            return self.render_one(error=400)
        if not self.strategy.allowed_on('write', instance):
            return self.render_one(error=401)
        form = self.form_class(request.form, obj=None)
        if not form.validate():
            return self.render_one(error=403)
        form.populate_obj(instance)
        instance.save()  
        return redirect()
    
    def delete(self, *args, **kwargs):
        instance = self.strategy.fetch_item(id)
        if not instance:
            return self.render_one(error=400)
        if not self.strategy.allowed_on('write', instance):
            return self.render_one(error=401)
        instance.delete()  
        return redirect()

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
        self.form_class = form_class if form_class else model_form(model_class)
        self.template = template if template else 'models/%s.html' % self.resource_name
        self.route = route

    def get_redirect_url(self, instance):
        return url_for(self.route, id=instance.id)

    def get_instance(self, id):
        return self.model_class.objects(id=id)

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
                print kwargs['resource']
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

class ModelRequest(View):
    methods = ['GET']
    def __init__(self, server, op):
        self.server = server
        self.op = op

    def dispatch_request(self, **view_args):
        if self.op in self.server.ops_by_identifier: # for view, edit, delete
            model_obj = self.server.get_obj(view_args[self.server.identifier])
        else:
            model_obj = None
        render_args = {}
        for p in self.server.parents:
            # Fetch model objects for all parents as well
            render_args[p.model_name] = p.get_obj(view_args[p.model_identifier])
        if request.method == 'GET':
            return self.server.render(self.op, model_obj, **render_args)
        elif request.method == 'POST':
            return self.server.commit(self.op, model_obj, **render_args)

class ModelServer:
    servers = {} # class global variable to remember all servers created
    op_messages = {'edit': 'edited', 'new': 'created', 'delete':'deleted'}

    @staticmethod
    def get_model_name(model_class):
        return model_class.__name__.lower().split('.')[-1] # class name, ignoring package name

    def __init__(self, app, model_class, parent=None, form_class=None, templatepath=None, model_request_class=None, allowed_func=None): # should allow override formclass, template, route
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
        self.parents = parent.parents + [parent] if parent else []
        if not templatepath:
            self.templatepath = parent.templatepath if parent else 'models/'
        else:
            self.templatepath = templatepath
        self.templates = {
            'list': '%s%s_list.html' % (self.templatepath, self.model_name),
            'new': '%s%s_view.html' % (self.templatepath, self.model_name),
            'view': '%s%s_view.html' % (self.templatepath,self.model_name),
            'edit': '%s%s_view.html' % (self.templatepath, self.model_name),
            'delete': 'includes/confirm.html',
            'base': '%sbase.html' % self.templatepath
        }
        if allowed_func:
            self.allowed = allowed_func
        self.ops_by_model = ['list','new']
        self.ops_by_identifier = ['view','edit','delete']

        ModelServer.servers[self.model_name] = self
        ModelServer.servers[self.model_identifier] = self # also findable by identifier

    def allowed(self, op, user, model_obj=None): # to be overriden
        if op in ['list','view']:
            return True
        else:
            print "According to default ModelServer, all state changing operations disallowed! Override method to change!"
            return True ## TODO false

    def get_obj(self, identifier):
        if self.identifier == 'slug':
            return self.model_class.objects.get_or_404(slug=identifier)
        else:
            return self.model_class.objects.get_or_404(id=identifier)

    def get_form(self, op, model_obj=None, req_form=None, **kwargs):
        if op=='edit' or op=='new':
            return self.form_class(req_form, obj=model_obj, **kwargs)
        else:
            return None 

# Redirect URL pattern
# [GET, POST] article/new -> article/<new_slug>/view -> view_article, world_slug=..., article_slug=...
# [GET] article/list (NO POST)
# [GET,POST] article/<s>/edit -> article/<s>/view
# [GET] article/<s>/view (NO POST)
# [GET, POST] article/<s>/delete -> article/

    def get_url(self, op, redir_args=None):
        args = request.view_args
        if redir_args:
            args.update(redir_args)
        endpoint = '.%s_%s' % (op, self.model_name)
        print endpoint
        return url_for(endpoint, **args)

    def render(self, op, model_obj, form=None, **render_args):
        print 'in render', op, model_obj
        if not self.allowed(op, auth.get_logged_in_user(), model_obj):
            return error_response("Not allowed to %s %s" % (op, model_obj))
        render_args['op'] = op
        if not form:
             # let's assume that the render args, e.g. view args, can be useful to pre-fill the form!
             # Below statement will pick the render args that match the parent model names, e.g. world, article
            form_args = { key: render_args[key] for key in [p.model_name for p in self.parents]}
            form = self.get_form(op, model_obj, **form_args)

        render_args[self.model_name+'_form'] = form
        
        render_args[self.model_name] = model_obj
        if request.args.has_key('inline'):
            render_args['inline'] = True
            render_args['template_parent'] = 'includes/inline.html'
        elif request.args.has_key('row'):
            render_args['row'] = True
            render_args['template_parent'] = 'includes/row.html'

        if op=='delete':
            return render_template('includes/confirm.html', url=request.base_url, #TODO, this will skip inline args, always intended? 
                action=op, model_objs={'model_obj':[model_obj]}, **render_args)
        else:
            return render_template(self.templates[op], **render_args)

    def commit(self, op, model_obj, form=None, **model_objs):
        user = auth.get_logged_in_user()
        if op=='edit' or op=='new':
            # Create form object based on request and existing model_obj
            form = form if form else self.get_form(op, model_obj, request.form)
            #print "In NEW resource %s %s %s" % (request.form, model_obj, self.form_class)
            if form.validate():
                if op=='new' and not model_obj: # create an model_obj if we won't have one yet
                    model_obj = self.model_class()
                form.populate_obj(model_obj)
                model_obj.save()
                flash(u'%s was successfully %s' % (model_obj, self.op_messages[op]), 'success')
                user.log(u'%s %s' % (self.op_messages[op], model_obj))
                # as slug/id may have been changed or just created, we need to add it to redirect args.
                # model_identifier refers to either ...slug or ...id
                redir_args = {self.model_identifier:getattr(model_obj, self.identifier)}
                return redirect(self.get_url('view', redir_args))
            else:
                return error_response(u'Input data %s to %s %s did not validate because of %s' % (request.form, op, self.model_class, form.errors))
        elif op=='delete':
            s = u'%s' % model_obj
            model_obj.delete_instance()
            flash(u'%s was successfully deleted' % s, 'success')
            user.log(u'deleted %s' % s)
            return redirect(self.get_url('list'))

    def autoregister_urls(self):
        self.add_op('list', self.model_request_class, verbose=True, on_instance=False)
        self.add_op('new', self.model_request_class, verbose=True, on_instance=False, methods=['GET','POST'])
        self.add_op('view', self.model_request_class, verbose=True, on_instance=True)
        self.add_op('edit', self.model_request_class, verbose=True, on_instance=True, methods=['GET','POST'])
        self.add_op('delete', self.model_request_class, verbose=True, on_instance=True, methods=['GET','POST'])

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