from flask_debugtoolbar.panels import DebugPanel
import pyinstrument
import pyinstrument.renderers
import os
import re

_ = lambda x: x


class PyinstrumentDebugPanel(DebugPanel):

    name = "Pyinstrument"
    has_content = True
    has_resource = True

    def __init__(self, jinja_env, context={}):
        # resources_dir = os.path.join(
        #     os.path.dirname(os.path.abspath(pyinstrument.renderers.__file__)), "html_resources/"
        # )
        # with open(os.path.join(resources_dir, "app.js"), encoding="utf-8") as f:
        #     self.js = f.read()
        # Patch JS to not set CSS on whole body
        # TODO could also possibly load an iframe with dynamically set HTML body
        # self.js = re.sub(r"body,html{.*?}", "", self.js)
        # set higher specificity on body,html and #app
        # self.js = self.js.replace(
        #     "body,html{background-color:#303538;color:#fff;padding:0;margin:0}#app{",
        #     "#flDebugPyinstrumentPanel-content, #flDebugPyinstrumentPanel-content * {background-color:#303538;color:#fff;padding:0;margin:0;",
        # )
        super(PyinstrumentDebugPanel, self).__init__(jinja_env, context)

    def nav_title(self):
        return _("Profiler")

    def nav_subtitle(self):
        return f"{self.session.sample_count} samples"

    def title(self):
        return _("Pyinstrument")

    def url(self):
        return ""

    def process_request(self, request):
        self.profiler = pyinstrument.Profiler()
        self.profiler.start()

    def process_response(self, request, response):
        self.profiler.stop()
        self.session = self.profiler._get_last_session_or_fail()

    def content(self):
        html_doc = self.profiler.output_html(timeline=True)
        html_doc = re.sub(r"<!DOC.+<body>", "", html_doc, flags=re.MULTILINE | re.DOTALL)
        html_doc = re.sub(r"</body>\s+</html>", "", html_doc)
        # html_doc = '<template id="pyinst-template>' + html_doc
        # html_doc += """
        # </template><div id="pyinst-div"></div>
        # <script>
        # var div = document.querySelector( "#pyinst-div" );
        # sh = div.attachShadow( { mode: "closed" } );
        # var template = document.querySelector( "#pyinst-template" );
        # sh.appendChild( template.content.cloneNode( true ) )
        # </script>
        # """
        # html_doc now contains <div id="app">...</div>
        # html_doc = re.sub(
        #     r"body,html",
        #     "#app, #app * { all: revert} #flDebugPyinstrumentPanel-content .flDebugPanelContent",
        #     html_doc,
        # )
        html_doc = re.sub(r"body,html", "#flDebugPyinstrumentPanel-content .flDebugPanelContent", html_doc)
        html_doc = re.sub(r"#app{", "#flDebugPyinstrumentPanel-content .flDebugPanelContent #app{", html_doc)
        html_doc = re.sub(r"\.frame\[", "#flDebugPyinstrumentPanel-content #app .frame[", html_doc)
        html_doc = re.sub(r"\.frame-", "#flDebugPyinstrumentPanel-content #app .frame-", html_doc)

        # html_doc = html_doc.replace("`", "\\\\`").replace("<", "\\x3C")
        # iframe = f"""
        # <script>
        # var iframe = document.createElement('iframe');

        # // div tag in which iframe will be added should have id attribute with value myDIV
        # document.getElementById("flDebugPyinstrumentPanel-content").appendChild(iframe);

        # // provide height and width to it
        # iframe.setAttribute("style","height:100%;width:100%;");
        # iframe.contentWindow.document.open();
        # iframe.contentWindow.document.write(`{html_doc}`);
        # iframe.contentWindow.document.close();
        # </script>
        # """
        return html_doc
