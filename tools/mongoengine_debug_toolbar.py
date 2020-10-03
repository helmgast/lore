from flask_debugtoolbar.panels import DebugPanel
from mongoengine.context_managers import query_counter
from flask import render_template

_ = lambda x: x


class MongoengineToolbar(DebugPanel):

    name = "MongoEngine"
    has_content = True
    has_resource = True

    def __init__(self, jinja_env, context={}):
        self.query_counter = query_counter()
        self.queries = []
        super(MongoengineToolbar, self).__init__(jinja_env, context)

    def nav_title(self):
        return _("Mongo")

    def nav_subtitle(self):
        return f"{len(self.queries)} queries made"

    def title(self):
        return _("Mongoengine")

    def url(self):
        return ""

    def process_request(self, request):
        self.query_counter._turn_on_profiling()

    def process_response(self, request, response):
        self.query_counter._resets_profiling()
        self.queries = list(self.query_counter.db.system.profile.find())

    def content(self):
        for q in self.queries:
            q["command"] = {k: v for k, v in q["command"].items() if k not in ["lsid", "$readPreference", "$db"]}
        # rows = (
        #     (_("Total queries"), self.query_counter),
        #     # (_('System CPU time'), '%0.3f msec' % stime),
        #     # (_('Total CPU time'), '%0.3f msec' % (utime + stime)),
        #     # (_('Elapsed time'), '%0.3f msec' % self.total_time),
        #     # (_('Context switches'), '%d voluntary, %d involuntary' % (vcsw, ivcsw)),
        #     # # ('Memory use', '%d max RSS, %d shared, %d unshared' % (rss, srss, urss + usrss)),
        #     # # ('Page faults', '%d no i/o, %d requiring i/o' % (minflt, majflt)),
        #     # # ('Disk operations', '%d in, %d out, %d swapout' % (blkin, blkout, swap)),
        # )

        # context = self.context.copy()
        # context.update({"rows": rows})

        return render_template("includes/mongoengine_panel.html", rows=self.queries)
