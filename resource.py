from flask import request, render_template, flash, redirect, url_for
from raconteur import auth, db
from flask.ext.mongoengine.wtf import model_form
from flask.ext.mongoengine.wtf.orm import ModelConverter, converts

from flask.views import View
from raconteur import the_app
from wtforms.compat import iteritems
from wtforms.fields import FormField
from wtforms import Form as OrigForm
import inspect


def generate_flash(action, name, model_identifiers, dest=''):
    s = u'%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1 else '', ', '.join(model_identifiers), u' to %s' % dest if dest else '')
    flash(s, 'success')
    return s

def error_response(msg, level='error'):
    flash(msg, level)
    return render_template('includes/inline.html')

# class CSRFDisabledModelForm(ModelForm):
#     """A Base Form class that disables CSRF by default, 
#     to be used for e.g. EmbeddedDocument models"""

#     def __init__(self, formdata=None, obj=None, prefix='', **kwargs):
#         super(CSRFDisabledModelForm, self).__init__(formdata, obj, prefix, csrf_enabled=False, **kwargs)

class RacFormField(FormField):
    def __init__(self, *args, **kwargs):
        # We need to save the form in the field to read from it later
        # (normally in WTForms, fields shouldn't know about their forms)
        self._form = kwargs['_form']
        # print "_form is %s" % kwargs['_form']
        super(RacFormField, self).__init__(*args, **kwargs)

    def populate_obj(self, obj, name):
        # print "Populating field %s of %s from formfield %s of form class %s (model class %s)" % (
        #        name, obj, self.name, self.form_class, self.form_class.model_class)
        candidate = getattr(obj, name, None)
        # print "Validated type in form is %s, type %s" % (self._form.type.data, type(self._form.type.data))
        # new_type = obj.is_type(self.name)
        typefield = self._form.model_class.create_type_name(self._form.type.data) + 'article'

        # If new type matches this field
        if typefield == name:
            # if this field has no object
            if candidate is None:
                # Create empty instance of this object based on Model Class
                candidate = self.form_class.model_class()
                setattr(obj, name, candidate)
                print "RacFormField.populate_obj: instantiated %s to new object as it was empty before, in %s" % (name, obj)
            # Then populate as usual
            self.form.populate_obj(candidate)
        # If new type is not this field
        elif not candidate is None:
            print "RacFormField.populate_obj: set %s to None as not type of %s" % (name, obj)
            # Just None the whole field and skip the population
            setattr(obj, name, None)

class RacModelConverter(ModelConverter):
    @converts('EmbeddedDocumentField')
    def conv_EmbeddedDocument(self, model, field, kwargs):
        kwargs = {
            'validators': [],
            'filters': [],
            'default': field.default or field.document_type_obj,
        }
        # The only difference to normal ModelConverter is that we use the original, 
        # insecure WTForms form base class instead of the CSRF enabled one from
        # flask-wtf. This is because we are in a FormField, and it doesn't require 
        # additional CSRFs.
        form_class = model_form(field.document_type_obj, converter=RacModelConverter(),
            base_class=OrigForm, field_args={}, )
        return RacFormField(form_class, **kwargs)

class ResourceAccessStrategy:

    def __init__(self, model_class, plural_name, id_field='id', form_class=None, parent_strategy=None, parent_reference_field=None):
        self.form_class = form_class if form_class else model_form(model_class)
        self.model_class = model_class
        self.resource_name = model_class.__name__.lower().split('.')[-1] # class name, ignoring package name
        self.plural_name = plural_name
        self.parent = parent_strategy
        self.id_field = id_field
        # The field name pointing to a parent resource for this resource, e.g. article.world
        self.parent_reference_field = self.parent.resource_name if (self.parent and not parent_reference_field) else None
        print 'Strategy created for "' + self.resource_name + '"'

    def get_url_path(self, part, op=None):
        parent_url = ('' if (self.parent is None) else self.parent.url_item(None))
        op_val = ('' if (op is None) else ('/' + op))
        url = parent_url + '/' + part + op_val
        return url

    def url_list(self, op=None):
        return self.get_url_path(self.plural_name, op)

    def url_item(self, op=None):
        return self.get_url_path(self.plural_name+'/<'+self.resource_name+'>', op)

    def item_template(self):
        return '%s_item.html' % self.resource_name

    def list_template(self):
        return '%s_list.html' % self.resource_name

    def query_item(self, **kwargs):
        id = kwargs[self.resource_name]
        return self.model_class.objects.get(**{self.id_field:id})

    def create_item(self):
        return self.model_class()

    def query_list(self, args):
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

    def query_parents(self, **kwargs):
        if not self.parent:
            return {}
        # Silently pop arg, if existing, relating to current resource
        kwargs.pop(self.resource_name, None) 
        grandparents = self.parent.query_parents(**kwargs)
        grandparents[self.parent.resource_name] = self.parent.query_item(**kwargs)
        #print "all parents %s" % grandparents 
        return grandparents

    def all_view_args(self, item):
        view_args = {self.resource_name : getattr(item, self.id_field)}
        if self.parent:
            view_args.update(self.parent.all_view_args(getattr(item, self.parent_reference_field)))
        return view_args
      
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


class ResourceHandler:

    def __init__(self, strategy):
        self.form_class = strategy.form_class
        self.strategy = strategy

    def register_index(self, app):
        st = self.strategy
        app.add_url_rule('/', methods=['GET'], view_func=self.get_list, endpoint='index')
        
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

    def render_list(self, list=None, parents=None, op=None):
        render_args = {self.strategy.plural_name:list, 'op':op}
        render_args.update(parents)
        return render_template(self.strategy.list_template(), **render_args)
    
    def render_one(self, item=None, parents=None, op=None, form=None):
        render_args = {self.strategy.resource_name:item, 'op':op}
        render_args[self.strategy.resource_name+'_form'] = form
        render_args.update(parents)
        return render_template(self.strategy.item_template(), **render_args)

    def get(self, **kwargs):
        item = self.strategy.query_item(**kwargs)
        parents = self.strategy.query_parents(**kwargs)
        if not self.strategy.allowed_on('read', item):
            return self.render_one(error=401)
        return self.render_one(item, parents)

    def get_edit(self, **kwargs):
        item = self.strategy.query_item(**kwargs)
        parents = self.strategy.query_parents(**kwargs)
        if not item:
            return self.render_one(error=400)
        if not self.strategy.allowed_on('write', item):
            return self.render_one(error=401)
        # TODO add prefill form functionality
        form = self.form_class(obj=item)
        form.action_url = url_for('.'+self.strategy.endpoint_name('post'), method='put', **kwargs)
        return self.render_one(item, parents, op='edit', form=form)
    
    def get_new(self, *args, **kwargs):
        # no existing item as we are creating new
        parents = self.strategy.query_parents(**kwargs)
        if not self.strategy.allowed_any('write'):
            return self.render_one(error=401)
        # TODO add prefill form functionality
        form = self.form_class(request.args, obj=None)
        form.action_url = url_for('.'+self.strategy.endpoint_name('post_new'), **kwargs)
        return self.render_one(parents=parents, op='new', form=form)

    def get_list(self, *args, **kwargs):
        parents = self.strategy.query_parents(**kwargs)
        if not self.strategy.allowed_any('read'):
            return self.render_one(error=401)
        # list_args = self.get_list_args()
        # if not list_args:
        #     return self.render_one(error=400)
        list = self.strategy.query_list(request.args)
        # Filter on allowed items?
        return self.render_list(list=list, parents=parents)

    def get_edit_list(self, *args, **kwargs):
        if not self.strategy.allowed_any('write'):
            return self.render_one(error=401)
          
        list_args = self.get_list_args()
        if not list_args:
            return self.render_one(error=400)    
        list = self.strategy.query_list(list_args)
        # Filter on allowed items?
        return self.render_list(op='edit', item=list)

    def post(self, *args, **kwargs):
        if request.args.has_key('method'):
            method = request.args.get('method')
            if method.upper() == 'PUT':
              return self.put(*args, **kwargs);
            elif method.upper() == 'PATCH':
              return self.patch(*args, **kwargs)
            elif method.upper() == 'DELETE':
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
            print form.errors
            print self.strategy.model_class._fields
            return self.render_one(error=403)
        item = self.strategy.create_item()
        form.populate_obj(item)
        item.save()
        print kwargs
        if 'next' in request.args:
            return redirect(request.args['next'])
        return redirect(url_for('.'+self.strategy.endpoint_name('get'), 
            **self.strategy.all_view_args(item)))

    def print_form_inputs(self, reqargs, formdata, obj):
        '''Debug helper method to compare the data from HTTP, form and obj'''
        reqkeys = reqargs.keys()
        formdatakeys = formdata.keys()
        objkeys = obj.__dict__.keys()
        joinedkeys = reqkeys + formdatakeys + objkeys
        joinedkeys = [k for k in joinedkeys if k[0]!='_']
        for k in joinedkeys:
            print "Key: %s" % k
            print "\tReq: %s" % (reqargs.getlist(k) if reqargs.has_key(k) else None)
            print "\tForm: %s" % (formdata.get(k) if formdata.has_key(k) else None)
            print "\tObj: %s" % (getattr(obj, k, None))
        # print "Joined keys: %s" % joinedkeys

    def put(self, *args, **kwargs):
        item = self.strategy.query_item(**kwargs)
        parents = self.strategy.query_parents(**kwargs)
        if not item:
            return self.render_one(error=400)
        if not self.strategy.allowed_on('write', item):
            return self.render_one(error=401)
        form = self.form_class(request.form, obj=item)
        # self.print_form_inputs(request.form, form.data, item)
        if not form.validate():
            print form.errors
            return self.render_one(error=403)
        form.populate_obj(item)
        item.save()
        if 'next' in request.args:
            return redirect(request.args['next'])
        # In case slug has changed, query the new value before redirecting!
        return redirect(url_for('.'+self.strategy.endpoint_name('get'), 
            **self.strategy.all_view_args(item)))

    def patch(self, *args, **kwargs):
        item = self.strategy.query_item(**kwargs)
        parents = self.strategy.query_parents(**kwargs)
        if not item:
            return self.render_one(error=400)
        if not self.strategy.allowed_on('write', item):
            return self.render_one(error=401)
        form = self.form_class(request.form, obj=item)
        if not form.validate():
            print form.errors
            return self.render_one(error=403)
        form.populate_obj(item)
        item.save()
        if 'next' in request.args:
            return redirect(request.args['next'])
        # In case slug has changed, query the new value before redirecting!
        return redirect(url_for('.'+self.strategy.endpoint_name('get'), 
            **self.strategy.all_view_args(item)))
    
    def delete(self, *args, **kwargs):
        item = self.strategy.query_item(**kwargs)
        if not item:
            return self.render_one(error=400)
        if self.strategy.parent:
            parents = self.strategy.query_parents(**kwargs)
            redir_url = url_for('.'+self.strategy.endpoint_name('get_list'), **self.strategy.parent.all_view_args(getattr(item, self.strategy.parent_reference_field)))
        else:
             redir_url = url_for('.'+self.strategy.endpoint_name('get_list'))
        if not self.strategy.allowed_on('write', item):
            return self.render_one(error=401)
        item.delete()
        if 'next' in request.args:
            return redirect(request.args['next'])
        # We have to build our redir_url first, as we can't read it out when item has been deleted
        return redirect(redir_url)

class ResourceHandler2(View):
    default_ops = ['view', 'form_new', 'form_edit', 'list', 'new', 'replace', 'edit', 'delete']
    ignored_methods = ['as_view', 'dispatch_request', 'parse_url', 'register_urls']

    def __init__(self, strategy):
        self.form_class = strategy.form_class
        self.strategy = strategy

    @classmethod
    def register_urls(cls, app, st):
        # We try to parse out any methods added to this handler class, which we will use as separate endpoints
        custom_ops = []
        for name, m in inspect.getmembers(cls, predicate=inspect.ismethod):
            if (not name.startswith("__")) and (not name in cls.ignored_methods) and (not name in cls.default_ops):
                app.add_url_rule(st.get_url_path(name), methods=['GET'], view_func=ResourceHandler2.as_view(st.endpoint_name(name), st))
                print st.get_url_path(name)

        app.add_url_rule(st.url_item(), methods=['GET'], view_func=ResourceHandler2.as_view(st.endpoint_name('view'), st))
        app.add_url_rule(st.url_list('new'), methods=['GET'], view_func=ResourceHandler2.as_view(st.endpoint_name('form_new'), st))
        # app.add_url_rule(st.url_list('edit'), methods=['GET'], view_func=ResourceHandler2.as_view(st.endpoint_name('get_edit_list'), st))
        app.add_url_rule(st.url_item('edit'), methods=['GET'], view_func=ResourceHandler2.as_view(st.endpoint_name('form_edit'), st))
        app.add_url_rule(st.url_list(), methods=['GET'], view_func=ResourceHandler2.as_view(st.endpoint_name('list'), st))
        app.add_url_rule(st.url_list(), methods=['POST'], view_func=ResourceHandler2.as_view(st.endpoint_name('new'), st))
        app.add_url_rule(st.url_item(), methods=['PUT','POST'], view_func=ResourceHandler2.as_view(st.endpoint_name('replace'), st))
        app.add_url_rule(st.url_item(), methods=['PATCH','POST'], view_func=ResourceHandler2.as_view(st.endpoint_name('edit'), st))
        app.add_url_rule(st.url_item(), methods=['DELETE','POST'], view_func=ResourceHandler2.as_view(st.endpoint_name('delete'), st))
        # GET, POST, PATCH, PUT, DELETE resource/<id>
        # GET, POST resource/resources

    def dispatch_request(self, *args, **kwargs):
        # If op is given by argument, we use that, otherwise we take it from endpoint
        # The reason is that endpoints are not unique, e.g. for a given URL there may be many endpoints
        # TODO unsafe to let us call a method based on request args!
        # if request.method == 'POST' and op in ['put', 'patch','delete']:
        #     print "GOT SPECIAL POST, method is %s, endpoint op is %s and arg op is %s" % (request.method, op, request.args.get('op'))
        r = self.parse_url(**kwargs)
        r = getattr(self, r['op'])(r)

        # render output
        if 'next' in r:
            return redirect(r['next'])
        else:
            return render_template(r['template'], **r)

    def parse_url(self, **kwargs):
        r = {'url_args':kwargs}
        if self.strategy.resource_name in kwargs:
            r['item'] = self.strategy.query_item(**kwargs)
            r[self.strategy.resource_name] = r['item']
        r['parents'] = self.strategy.query_parents(**kwargs)
        r.update(r['parents'])
        r['op'] = request.args.get('op', request.endpoint.split('.')[-1].split('_',1)[-1].lower())
        if 'next' in request.args:
            r['next'] = request.args['next']
        return r

    def view(self, r):
        item = r['item']
        if not self.strategy.allowed_on(r['op'], item):
            return {'error':401}

        r['template'] = self.strategy.item_template()
        return r

    def form_edit(self, r):
        item = r['item']
        if not item:
            return {'error':400}
        if not self.strategy.allowed_on(r['op'], item):
            return {'error':401}
        # TODO add prefill form functionality
        form = self.form_class(obj=item)
        form.action_url = url_for('.'+self.strategy.endpoint_name('edit'), op='edit', **r['url_args'])
        r[self.strategy.resource_name+'_form'] = form
        r['op'] = 'edit' # form_edit is not used in templates...
        r['template'] = self.strategy.item_template()
        return r
    
    def form_new(self, r):
        if not self.strategy.allowed_any(r['op']):
            return {'error':401}
        # TODO add prefill form functionality
        form = self.form_class(request.args, obj=None)
        form.action_url = url_for('.'+self.strategy.endpoint_name('new'), **r['url_args'])
        r[self.strategy.resource_name+'_form'] = form
        r['op'] = 'new' # form_new is not used in templates...
        r['template'] = self.strategy.item_template()
        return r

    def list(self, r):
        if not self.strategy.allowed_any(r['op']):
            return {'error':401}
        r['list'] = self.strategy.query_list(request.args)
        r['template'] = self.strategy.list_template()
        r[self.strategy.plural_name] = r['list']
        # Filter on allowed items?
        return r

    def new(self, r):
        if not self.strategy.allowed_any(r['op']):
            return {'error':401}
        form = self.form_class(request.form, obj=None)
        if not form.validate():
            return {'error':403}
        item = self.strategy.create_item()
        form.populate_obj(item)
        item.save()
        if not 'next' in r:
            r['next'] = url_for('.'+self.strategy.endpoint_name('view'), **self.strategy.all_view_args(item))
        return r

    # TODO implement proper patch, currently just copy of PUT
    def edit(self, r):
        item = r['item']
        if not item:
            return {'error':400}
        if not self.strategy.allowed_on(r['op'], item):
            return {'error':401}
        form = self.form_class(request.form, obj=item)
        if not form.validate():
            return {'error':403}
        form.populate_obj(item)
        item.save()
        # In case slug has changed, query the new value before redirecting!
        if not 'next' in r:
            r['next'] = url_for('.'+self.strategy.endpoint_name('view'), **self.strategy.all_view_args(item))
        return r

    def replace(self, r):
        item = r['item']
        if not item:
            return {'error':400}
        if not self.strategy.allowed_on(r['op'], item):
            return {'error':401}
        form = self.form_class(request.form, obj=item)
        # self.print_form_inputs(request.form, form.data, item)
        if not form.validate():
            return {'error':403}
        form.populate_obj(item)
        item.save()
        if not 'next' in r:
            # In case slug has changed, query the new value before redirecting!
            r['next'] = url_for('.'+self.strategy.endpoint_name('view'), **self.strategy.all_view_args(item))
        return r

    def delete(self, r):
        item = r['item']
        if not item:
            return {'error':400}
        if not 'next' in r:
            if 'parents' in r:
                r['next'] = url_for('.'+self.strategy.endpoint_name('list'), **self.strategy.parent.all_view_args(getattr(item, self.strategy.parent_reference_field)))
            else:
                 r['next'] = url_for('.'+self.strategy.endpoint_name('list'))
        if not self.strategy.allowed_on(r['op'], item):
            return {'error':401}
        item.delete()
        return r

