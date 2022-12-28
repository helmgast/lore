from enum import Enum, IntEnum
from timeit import default_timer as timer
import traceback
from collections import Counter
from dataclasses import dataclass
from unicodedata import normalize
import json


def pretty_dict(dct):
    if isinstance(dct, dict):
        return json.dumps(dct, indent=2)
    else:
        return dct.__repr__()


class JobSuccess(Enum):
    SUCCESS = 0
    WARN = 1
    FAIL = 2
    SKIP = 3


class LogLevel(IntEnum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3


class Color:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARN = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


OK = f"{Color.OKGREEN}✓"
SKIP = f"{Color.OKBLUE}-"
FAIL = f"{Color.FAIL}✗"
WARN = f"{Color.WARN}⚠"

TERMINAL_WIDTH = 160


@dataclass
class Column:
    header: str = ""
    import_key: str = ""
    result_key: str = ""


def universal_get(data, key, default=None):
    if isinstance(data, dict):
        return data.get(key, default)
    else:
        return getattr(data, key, default)


class Job:
    def __init__(
        self, i: int = 0, batch=None, is_debug: bool = False, is_dry_run: bool = False, test_context: dict = None
    ):
        self.i = i
        self.data = {}
        self.log = []
        self.id = ""
        self.result = None
        self.success = JobSuccess.SUCCESS
        self.batch = batch
        self.test_context = test_context if test_context else {}
        self.is_debug = batch.is_debug if batch else is_debug
        self.is_dry_run = batch.is_dry_run if batch else is_dry_run
        self.is_bugreport = batch.is_bugreport if batch else False
        self.committer = None

    @property
    def context(self):
        return self.batch.context if self.batch else self.test_context

    def get_str(self, target_level=LogLevel.INFO):
        logs = "\n" + "\n".join(f"{level.name}: {msg}" for (level, msg) in self.log if level >= target_level)
        logs = logs.replace("\n", "\n    ")  # Indent all lines equally, even if the log message include line breaks
        return f"JOB-{self.i}: '{self.id}'->{self.success.name}{logs}\n"

    def get_row(self, columns=None, target_level=LogLevel.INFO):
        """Prints job results as table row. Takes an iterable representing columns.
        It will use the item in that column (or item.result_key) to populate the table row from the
        job.result property (so it needs to have the column values as fields or dict keys).
        If warnings/error it will print additional indented rows"""

        columns = columns or self.batch.context.get("columns", None)
        if not columns:
            raise ValueError("Needs a columns iterable to print as table")

        out = ""
        if self.success == JobSuccess.SUCCESS:
            out += OK
        elif self.success == JobSuccess.SKIP:
            out += SKIP
        elif self.success == JobSuccess.WARN:
            out += WARN
        else:
            out += FAIL
        out += f" {str(self.i).zfill(4)} "
        if self.result is None:
            # Take data from import instead, because we likely had an error in the import
            results = [universal_get(self.data, col.import_key, "?") for col in columns]
        else:
            results = [
                universal_get(self.result, col.result_key, universal_get(self.data, col.import_key, "?"))
                for col in columns
            ]

        for i, item in enumerate(results):
            col_width = int(TERMINAL_WIDTH * self.batch.col_weights[i])
            out += normalize("NFC", str(item))[0 : col_width - 1].ljust(col_width, " ")
        if self.success == JobSuccess.FAIL:
            errors = "\n    ".join(map(str, self.get_log(LogLevel.ERROR)))
            out += f"\n    {Color.FAIL}{errors}{Color.ENDC}"
            if self.is_debug:
                out += pretty_dict(self.data)
        if self.success == JobSuccess.WARN:
            warnings = "\n    ".join(map(str, self.get_log(LogLevel.WARN)))
            out += f"\n    {warnings}"
        info = "\n".join(map(str, self.get_log(LogLevel.INFO)))
        if info:
            out += f"\n    {info}"
        out += Color.ENDC
        return out

    def __str__(self):
        return self.get_str()

    def get_log(self, level):
        return [msg for lvl, msg in self.log if lvl == level]

    def warn(self, s):
        self.success = JobSuccess.WARN
        self.log.append((LogLevel.WARN, s))

    def error(self, s):
        self.success = JobSuccess.FAIL
        self.log.append((LogLevel.ERROR, s))

    def info(self, s):
        self.log.append((LogLevel.INFO, s))

    def debug(self, s):
        self.log.append((LogLevel.DEBUG, s))


def bulk_update(doc_class, docs):
    from pymongo import UpdateOne
    from mongoengine import Document, ValidationError

    bulk_operations = []

    for doc in docs:
        if doc:
            try:
                doc.validate()
                doc.clean()
                bulk_operations.append(UpdateOne({"_id": doc.id}, {"$set": doc.to_mongo().to_dict()}, upsert=True))
            except ValidationError as ve:
                print(ve)

    if bulk_operations:
        return doc_class._get_collection().bulk_write(bulk_operations, ordered=False)
    else:
        return None


class Batch:
    def __init__(
        self,
        name,
        log_level=LogLevel.WARN,
        dry_run=True,
        bugreport=False,
        table_columns=None,
        no_metadata=False,
        limit=0,
        **kwargs,
    ):
        self.name = name
        self.log_level = log_level if isinstance(log_level, LogLevel) else LogLevel[log_level]
        self.context = kwargs
        self.jobs = []
        self.is_bugreport = bugreport
        self.is_debug = self.log_level is LogLevel.DEBUG or bugreport
        self.is_dry_run = dry_run
        self.limit = int(limit)

        if table_columns is not None and (
            not isinstance(table_columns, list) or len(table_columns) == 0 or not isinstance(table_columns[0], Column)
        ):
            raise ValueError(f"Invalid column data provided {table_columns}")
        self.table_columns = table_columns
        self.no_metadata = no_metadata

    def process(self, generator, job_func, *args, **kwargs):
        self.start = timer()
        intro = ""
        if self.table_columns:
            self.col_weights = []
            for col in self.table_columns:
                if (col.header.endswith(" ") or col.header.endswith("_")) and len(col.header) > 0:
                    self.col_weights.append(len(col.header))
                else:
                    self.col_weights.append(1)
            sum_weights = sum(self.col_weights)
            self.col_weights = [w / sum_weights for w in self.col_weights]

            intro = f"       {self.name}{' DRY RUN' if self.is_dry_run else ''}{' DEBUG' if self.is_debug else ''}\n\n"
            intro += "       "
            for i, col in enumerate(self.table_columns):
                col_width = int(TERMINAL_WIDTH * self.col_weights[i])
                intro += col.header[: col_width - 1].ljust(col_width, " ")
            intro += "\n       "
            for i, col in enumerate(self.table_columns):
                col_width = int(TERMINAL_WIDTH * self.col_weights[i])
                intro += "".ljust(col_width - 1, "-") + " "
        else:
            intro += f"{self.name}{' DRY RUN' if self.is_dry_run else ''}{' DEBUG' if self.is_debug else ''}\n"
        print(intro)

        for i, data in enumerate(generator):
            if self.limit > 0 and i > self.limit:
                break
            job = Job(i, self)
            self.jobs.append(job)
            try:
                job.data = data
                job.result = job_func(job, data, **kwargs)
            except Exception as e:
                # err_msg = f"Error in job with data='{data}'\n"
                if self.is_debug:
                    job.error(traceback.format_exc())
                else:
                    job.error(e)

            if job.success is not JobSuccess.SKIP:
                if self.table_columns:
                    print(job.get_row(self.table_columns))
                else:
                    print(job.get_str(self.log_level))
        self.end = timer()
        self.elapsed = self.end - self.start

    def commit(self):
        for job in self.jobs:
            if job.committer:
                job.committer()

    def cur_job(self):
        return self.jobs[-1] if len(self.jobs) else None

    def summary_str(self):
        counts = Counter(job.success for job in self.jobs)
        rv = (
            f"---------------------\n"
            f"Summary: '{self.name}'{' DRY RUN' if self.is_dry_run else ''}{' DEBUG' if self.is_debug else ''}\n"
            f"SUCCESS {counts[JobSuccess.SUCCESS]} job(s)\n"
            f"WARN    {counts[JobSuccess.WARN]} job(s)\n"
            f"FAIL    {counts[JobSuccess.FAIL]} job(s)\n"
            f"SKIP    {counts[JobSuccess.SKIP]} job(s)\n"
            f"---------------------\n"
            f"TOTAL   {len(self.jobs)} job(s)\n"
            f"Elapsed time: {self.elapsed:.2f}s"
        )
        return rv
