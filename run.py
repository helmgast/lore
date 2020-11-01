import os
import re
import shlex
import subprocess as sp
import sys
import click

from lore.app import create_app
from tools.batch import Batch, Column, LogLevel, bulk_update


# from https://blog.theodo.com/2020/05/debug-flask-vscode/
def initialize_flask_server_debugger_if_needed():
    if os.getenv("LORE_DEBUG") == "True":
        import multiprocessing

        if multiprocessing.current_process().pid > 1:
            import debugpy

            debugpy.listen(("0.0.0.0", 10001))
            print("⏳ VS Code debugger can now be attached, press F5 in VS Code ⏳", flush=True)
            # debugpy.wait_for_client()
            # print("🎉 VS Code debugger attached, enjoy debugging 🎉", flush=True)


initialize_flask_server_debugger_if_needed()
app = create_app()


def runshell(cmd):
    cmdsplit = shlex.split(cmd)
    cp = sp.run(cmdsplit)
    if cp.returncode > 0:
        sys.exit(cp.returncode)


@app.cli.command()
def initdb():
    """Initialize the database."""
    click.echo("Init the db")


@app.cli.command()
@click.option("-u", "--url", required=False, help="Test an URL for which route it picks")
@click.option("-m", "--method", required=False, default="GET", help="Method to test")
def show_routes(url, method):
    from urllib.parse import urlparse

    rows = [
        (str(i), rule.__repr__().replace("LoreRule ", ""), str(rule.match_compare_key()))
        for i, rule in enumerate(sorted(app.url_map.iter_rules(), key=lambda rule: rule.match_compare_key()))
    ]
    widths = [max(map(len, col)) for col in zip(*rows)]
    parts, adapter = None, None
    if url:
        parts = urlparse(url)
        adapter = app.url_map.bind(parts.netloc, path_info=parts.path, url_scheme=parts.scheme, query_args=parts.query)
        matched_rule, arguments = adapter.match(return_rule=True)
        print("\n", matched_rule.__repr__(), arguments, "\n")
    rows.insert(0, ("", "", "No arg?, static parts, static lenghts, arg parts, arg weights"))
    for row in rows:
        test = ""
        if adapter:
            test = "Y " if matched_rule.__repr__().replace("LoreRule ", "") == row[1] else "N "
        print(test + "  ".join((val.ljust(width) for val, width in zip(row, widths))))


# @app.cli.command()
# @click.option('--host', '-h', default='127.0.0.1',
#               help='The interface to bind to.')
# @click.option('--port', '-p', default=5000,
#               help='The port to bind to.')
# @click.option('--reload/--no-reload', default=None,
#               help='Enable or disable the reloader.  By default the reloader '
#               'is active if debug is enabled.')
# @click.option('--debugger/--no-debugger', default=None,
#               help='Enable or disable the debugger.  By default the debugger '
#               'is active if debug is enabled.')
# @click.option('--eager-loading/--lazy-loader', default=None,
#               help='Enable or disable eager loading.  By default eager '
#               'loading is enabled if the reloader is disabled.')
# @click.option('--with-threads/--without-threads', default=False,
#               help='Enable or disable multithreading.')
# @click.option('--watch', default=None, multiple=True,
#               help='Add files to watch for reload')
# @pass_script_info
# def runwatch(info, host, port, reload, debugger, eager_loading,
#                 with_threads, watch):
#     from werkzeug.serving import run_simple

#     debug = get_debug_flag()
#     if reload is None:
#         reload = bool(debug)
#     if debugger is None:
#         debugger = bool(debug)
#     if eager_loading is None:
#         eager_loading = not reload

#     app = DispatchingApp(info.load_app, use_eager_loading=eager_loading)

#     # Extra startup messages.  This depends a bit on Werkzeug internals to
#     # not double execute when the reloader kicks in.
#     if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
#         # If we have an import path we can print it out now which can help
#         # people understand what's being served.  If we do not have an
#         # import path because the app was loaded through a callback then
#         # we won't print anything.
#         if info.app_import_path is not None:
#             print(' * Serving Flask app "%s"' % info.app_import_path)
#         if debug is not None:
#             print(' * Forcing debug mode %s' % (debug and 'on' or 'off'))

#     run_simple(host, port, app, use_reloader=reload,
#                use_debugger=debugger, threaded=with_threads, extra_files=watch)


@app.cli.command()
def lang_extract():  # Run as lang-extract
    """Extract translatable strings and .PO files for predefined locales (SV).
    After running this, go to the .PO files in lore/translations/ and manually
    translate all empty MsgId. Then run python manage.py lang_compile
    """

    # TODO use python path environment instead of venv
    runshell(
        "venv/bin/pybabel extract --no-wrap --sort-by-file -F lore/translations/babel.cfg -o temp.pot lore/ plugins/"
    )
    runshell("venv/bin/pybabel update -i temp.pot -d lore/translations -l sv --no-fuzzy-matching")
    runshell("rm temp.pot")
    print()
    print("New strings needing translation:")
    print("------------------------")
    with open("lore/translations/sv/LC_MESSAGES/messages.po") as f:
        s = f.read()
        for m in re.findall(r'msgid ((".*"\s+)+)msgstr ""\s\s', s):
            print(m[0].split("/n")[0])  # avoid too long ones


@app.cli.command()
def lang_compile():  # Run as lang-compile
    """Compiles all .PO files to .MO so that they will show up at runtime."""

    runshell("pybabel compile -d lore/translations -l sv")


@app.cli.command()
@click.option("--reset", default=False, help="Reset database, WILL DESTROY DATA")
def db_setup(reset=False):
    """Setup a new database with starting data"""
    from mongoengine.connection import get_db
    from lore.extensions import db_config_string

    print(db_config_string)
    db = get_db()
    # Check if DB is empty
    # If empty, insert an admin user and a default world
    from lore.model.user import User, UserStatus
    from lore.model.world import World

    if len(User.objects(admin=True)) == 0:  # consider the database empty
        admin_password = app.config["SECRET_KEY"]
        admin_email = app.config["MAIL_DEFAULT_SENDER"]
        print(
            dict(
                username="admin",
                password="<SECRET KEY FROM CONFIG>",
                email=app.config["MAIL_DEFAULT_SENDER"],
                admin=True,
                status=UserStatus.active,
            )
        )

        u = User(
            username="admin",
            password=app.config["SECRET_KEY"],
            email=app.config["MAIL_DEFAULT_SENDER"],
            admin=True,
            status=UserStatus.active,
        )
        u.save()
        World(title="Helmgast")  # Create the default world

    # Else, if reset, drop all collections
    elif reset:
        # Drop all collections but not the full db as we'll lose user table then
        for c in db.collection_names(False):
            app.logger.info("Dropping collection %s" % c)
            db.drop_collection(c)
        from tools.dummy_data import model_setup

        model_setup.setup_models()

        # This hack sets a unique index on the md5 of image files to prevent us from
        # uploading duplicate images
        # db.connection[the_app.config['MONGODB_SETTINGS']['DB']]['images.files'].ensure_index(
        #        'md5', unique=True, background=True)


@app.cli.command()
def validate_model():
    from mongoengine import Document

    is_ok = True
    # Look for model classes in these packages
    pkgs = ["model.misc", "model.user", "model.world"]
    for doc in Document._subclasses:  # Ugly way of finding all document type
        if doc != "Document":  # Ignore base type (since we don't own it)
            for pkg in pkgs:
                try:
                    cls = getattr(
                        __import__(pkg, fromlist=[doc]), doc
                    )  # Do add-hoc import/lookup of type, simillar to from 'pkg' import 'doc'
                    try:
                        cls.objects()  # Check all objects of type
                    except TypeError:
                        logger.error("Failed to instantiate %s", cls)
                        is_ok = False
                except AttributeError:
                    pass  # Ignore errors from getattr
                except ImportError:
                    pass  # Ignore errors from __import__
    logger.info("Model has been validated" if is_ok else "Model has errors, aborting startup")
    return is_ok


@app.cli.command()
def import_csv():
    from tools import customer_data
    from mongoengine.connection import get_db

    app.logger.info("Importing customer data")
    print(app.config["MONGODB_SETTINGS"])
    get_db()
    customer_data.setup_customer()


@app.cli.command()
@click.argument("url_or_id", required=True)
@click.argument("model", required=True)
@click.option("-s", "--sheet", required=False, help="Name or index of worksheet, if URL lacks #gid=x parameter")
@click.option(
    "-r", "--repeat_on_empty", is_flag=True, help="If a cell is empty in a row with data, repeat value from row above"
)
@click.option("-c", "--commit", is_flag=True, help="If given, will commit import.")
@click.option("--log-level", default="INFO")
@click.option("-l", "--limit", default=10, type=int, help="Maximum amounts of items to import")
@click.option("--publisher", required=False, help="Publisher domain to associate import with")
@click.option("--vatRate", required=False, help="VAT Rate to apply to all orders")
@click.option("--title", required=False, help="Overall import title")
@click.option("--sourceUrl", required=False, help="Source URL to add to all orders")
@click.option("--if-newer", required=False, type=bool, default=True, help="Only update if newer")
@click.option(
    "-b",
    "--default-bases",
    multiple=True,
    default=[],
    help="If an ID lacks base URI, search for it in these bases in order. If no match, add last one as base.",
)
@click.option(
    "-s",
    "--default-scopes",
    multiple=True,
    default=[],
    help="Comma separated list of scope id:s to add to all imported characteristics, e.g. user, lang, etc.",
)
@click.option(
    "-a",
    "--default-associations",
    multiple=True,
    default=[],
    help="Comma separated list of association statements as per LTM. 'This topic' part will be ignored.",
)
def import_sheet(url_or_id, model, **kwargs):
    from tools.import_sheets import import_data
    from mongoengine.connection import get_db
    from lore import extensions

    extensions.db.init_app(app)
    db = get_db()
    import_data(url_or_id, model, **kwargs)


@app.cli.command()
@click.argument("model", required=True)
@click.option("-c", "--commit", is_flag=True, help="If given, will commit import.")
@click.option("--log-level", default="INFO")
@click.option("--limit", default=10, type=int, help="Maximum amounts of items to import")
@click.option("--filter", help="Free text wildcard pattern to filter which items to import")
@click.option("--publisher", required=False, help="Publisher domain to associate import with")
@click.option("--vatrate", required=False, help="VAT Rate to apply to all orders")
@click.option("--title", required=False, help="Overall import title")
@click.option("--sourceurl", required=False, help="Source URL to add to all orders")
def import_textalk(model, **kwargs):
    from tools.import_textalk import import_articles, import_orders
    from mongoengine.connection import get_db
    from lore import extensions

    extensions.db.init_app(app)
    db = get_db()
    if model == "product":
        import_articles(**kwargs)
    elif model == "order":
        import_orders(**kwargs)
    else:
        raise ValueError(f"Unsupported data type {model} given")


@app.cli.command()
def setup_topics():
    from mongoengine.connection import get_db
    from lore import extensions
    from lore.model.topic import Topic, create_basic_topics

    extensions.db.init_app(app)
    db = get_db()

    basic_topics = create_basic_topics()
    bulk_update(Topic, basic_topics.values())


@app.cli.command()
@click.argument("path", required=True)
@click.option("-c", "--commit", is_flag=True, help="If given, will commit import.")
@click.option("--log-level", default="WARN")
@click.option("--ignore-dates", is_flag=True, help="Ignores dates from YAML in import Markdown")
@click.option("-l", "--limit", default=0, help="Only process this many jobs")
@click.option("-m", "--match", default="", help="Only process jobs with this match string in id")
@click.option("--github-wiki", default="", help="The path to a github wiki where this is sourced")
@click.option(
    "-b",
    "--default-bases",
    multiple=True,
    default=[],
    help="If an ID lacks base URI, search for it in these bases in order. If no match, add last one as base.",
)
@click.option(
    "-s",
    "--default-scopes",
    multiple=True,
    default=[],
    help="Comma separated list of scope id:s to add to all imported characteristics, e.g. user, lang, etc.",
)
@click.option(
    "-a",
    "--default-associations",
    multiple=True,
    default=[],
    help="Comma separated list of association statements as per LTM. 'This topic' part will be ignored.",
)
def import_markdown_topics(path, **kwargs):
    from lore.model.topic import LORE_BASE, Topic, TopicFactory
    from lore.model.import_topic import job_import_topic
    from mongoengine.connection import get_db
    from lore import extensions
    import pathlib
    import frontmatter

    extensions.db.init_app(app)
    db = get_db()

    columns = [
        Column("ID", "id", "id"),
        Column("TITLE", "title", "name"),
        Column("CREATED", "created_at", "created_at"),
    ]

    # Adds list of scopes to all characteristics, e.g. "community-content" or a specific author.
    commit = kwargs.pop("commit", False)
    match = kwargs.pop("match")
    default_bases = kwargs.pop("default_bases")
    default_scopes = kwargs.pop("default_scopes")
    default_associations = kwargs.pop("default_associations")
    factory = TopicFactory(default_bases, default_scopes, default_associations)

    b = Batch(
        f"Import markdown files from path {path}",
        table_columns=columns,
        dry_run=not commit,
        topic_factory=factory,
        **kwargs,
    )

    def doc_generator(markdown_files_path, match):
        p = pathlib.Path(markdown_files_path)
        for file in p.glob("**/*.md"):
            doc = frontmatter.load(file)
            if "id" not in doc.keys():
                doc["id"] = file.stem
            if not match or match in doc["id"]:
                yield doc

    b.process(doc_generator(path, match), job_import_topic)
    if commit:
        bulk_update(Topic, factory.topic_dict.values())

    print(b.summary_str())


@app.cli.command()
@click.argument("wiki_xml_file", required=True)
@click.argument("output_folder", required=True)
@click.argument("filter", required=False)
@click.option("--dry-run", is_flag=True)
@click.option("--log-level", default="WARN")
@click.option("--bugreport", is_flag=True)
@click.option("--no-metadata", is_flag=True)
def wikitext_to_markdown(wiki_xml_file, output_folder, filter, dry_run, log_level, bugreport, no_metadata):
    from tools.batch import Batch, Column
    from tools.import_mediawiki import wikitext_generator, job_wikitext_to_markdown

    # from mongoengine.connection import get_db
    # from lore import extensions
    # extensions.db.init_app(app)
    # db = get_db()

    # No need, let user pick their exact folder instead
    out_folder = os.path.abspath(output_folder)
    # out_folder = os.path.join(output_folder, os.path.splitext(os.path.basename(wiki_xml_file))[0])
    # os.makedirs(out_folder, exist_ok=True)
    columns = [Column(header="Title", import_key="title"), Column(header="Path", result_key="path")]
    b = Batch(
        f"Wikitext to Markdown: {wiki_xml_file}",
        log_level=log_level,
        dry_run=dry_run,
        table_columns=columns,
        bugreport=bugreport,
        no_metadata=no_metadata,
        filter=filter,
        all_pages={},
        out_folder=out_folder,
    )
    b.process(wikitext_generator(wiki_xml_file), job_wikitext_to_markdown)
    print(b.summary_str())


@app.cli.command()
def db_migrate():
    from tools import db_migration
    from mongoengine.connection import get_db
    from lore import extensions

    extensions.db.init_app(app)
    db = get_db()
    # Ensure we have both app context and a (dummy) request context
    with app.app_context():
        with app.test_request_context("/"):
            db_migration.db_migrate(db)


@app.cli.command()
def test():
    """Run all unit tests on Lore"""
    from tests import app_test
    import unittest

    suite = unittest.TestLoader().loadTestsFromTestCase(app_test.LoreTestCase)
    unittest.TextTestRunner(verbosity=2).run(suite)


@app.cli.command()
@click.option("--email", help="Set a new password)")
def set_password(email):
    if not app.debug:
        print("We don't allow changing passwords if not in debug mode")
        exit(1)
    from lore.model.user import User

    user = User.query_user_by_email(email=email).first()
    if user:
        passw = prompt_pass("Enter the new password")
        if passw and len(passw) > 4:
            user.password = passw
            user.save()
        else:
            print("Too short or no password provided")
    else:
        print("No such user")


@app.cli.command()
@click.option("--file", help="The file to upload to the database")
@click.option("--title", help="Title of the file")
@click.option("--desc", help="Description of the file")
@click.option("--access", help="Access type, either public, product or user")
def file_upload(file, title, desc, access):
    """Adds a file asset from command line to the GridFS database"""
    from lore.model.asset import FileAsset, FileAccessType
    import mimetypes

    if not file or not os.access(file, os.R_OK):  # check read access
        raise ValueError("File %s not readable" % file)

    access = access if access in FileAccessType else "public"
    fname = os.path.basename(file)
    if not title:
        title = fname
    fa = FileAsset(title=title, description=desc, source_filename=fname, attachment_filename=fname, access_type=access)
    mime = mimetypes.guess_type(fname)[0]
    fa.file_data.put(open(file), filename=fname, content_type=mime)
    fa.save()
    print(file, title, desc)
    # print file, title, description


@app.cli.command()
@click.option("--output", help="File path to write new PDF to")
@click.option("--input", help="PDF file to fingerprint (will not change input)")
@click.option("--user", help="User ID to fingerprint with", required=True)
def pdf_fingerprint(input, output, user):
    """Will manually fingerprint a PDF file."""
    print("Fingerprinting user %s from file %s into file %s" % (user, input, output))
    with open(output, "wb") as f:
        with open(input, "rb") as f2:
            for buf in fingerprint_pdf(f2, user):
                f.write(buf)


@app.cli.command()
@click.option("--input", help="PDF file to check for fingerprints")
def pdf_check(input):
    """Will scan a PDF for matching fingerprints"""
    fps = get_fingerprints(input)
    from lore.model.user import User

    users = list(User.objects().only("id", "username"))
    # users.append('ripperdoc@gmail.com')
    # print users
    for user in users:
        uid = fingerprint_from_user(user.id)
        print("User %s with id %s got fp %s" % (user, user.id, uid))
        for fp in fps:
            if uid == fp:
                print("User %s matches fingerprint %s in document %s" % (user, fp, input))
                exit(1)
    print("No match for any user in document %s" % (input))
