from flask import request, render_template, flash, redirect
from auth import auth

def generate_flash(action, name, model_identifiers, dest=''):
    s = '%s %s%s %s%s' % (action, name, 's' if len(model_identifiers) > 1 else '', ', '.join(model_identifiers), ' to %s' % dest if dest else '')
    flash(s, 'success')
    return s

def error_response(msg, level='error'):
    flash(msg, level)
    return render_template('includes/partial.html')

class ResourceHandler:
    # four operations on model
    # view (view without form, e.g. static)
    # edit (view with form, and post to that form)
    # new (view form for new instance and post to that form)
    # delete (remove instance)
    op_messages = {'edit': 'edited', 'new': 'created', 'delete':'deleted'}
    model_class = None # needs to be overriden
    form_class = None # needs to be overriden

    def __init__(self, template, instance=None):
        self.template = template
        self.instance = instance
        self.form = None

    def field(self, name, non_editable=False, **kwargs):
        if non_editable or not self.form: # just print the value
            return getattr(self.instance, name)
        else: # print the form
            return getattr(self.form, name)(**kwargs)

    def get_form(self, op): # to be overriden
        return self.form_class(obj=self.instance)

    def prepare_get(self, op): # to be overriden
        pass

    def after_post(self, op): # to be overriden
        pass

    def allowed(self, op, user, instance=None): # to be overriden
        return False

    def handle_request(self, op='view'):
        if not self.instance and not op=='new':
            raise TypeError("Cannot handle operation %s without instance" % op)
        GET, POST = (request.method == 'GET'), request.method == 'POST'
        self.user = auth.get_logged_in_user()
        allowed = self.allowed(op, self.user, self.instance)
        if op=='edit' and not allowed and self.allowed('view', self.user, self.instance):
            op = 'view' # revert to view if we can't edit but still allowed to view
        elif not allowed:
            return error_response("You are not allowed to %s %s" % (op, self.instance if self.instance else self.model_class))
        self.op = op
        if GET:
            if op=='edit' or op=='new':
                self.form = self.get_form(op)
            self.prepare_get(op)
            if op=='delete':
                return render_template('includes/change_members.html', action=op, instances={'instance':self.instance})
            else:
                return render_template(self.template, resource=self, modal=request.args.has_key('modal'))
        elif POST:
            if op=='edit' or op=='new':
                self.form = self.form_class(request.form, obj=self.instance)
                if self.form.validate():
                    if op=='new': # create an instance as we won't have one yet
                        self.instance = self.model_class()
                    self.form.populate_obj(self.instance)
                    self.instance.save()
                    self.after_post(op)
                    flash("%s was successfully %s" % (self.instance, self.op_messages[op]), 'success')
                    self.user.log("%s %s" % (self.op_messages[op], self.instance))
                    print "Redirecting to %s" % request.base_url
                    return redirect(request.base_url)
                else:
                    return error_response("Input data to %s %s was incorrect" % (op,self.model_class))
            elif op=='delete':
                s = "%s" % self.instance
                self.instance.delete_instance()
                flash("%s was successfully deleted" % s, 'success')
                self.user.log("deleted %s" % s)
                redirect(request.base_url)
        return "Error"