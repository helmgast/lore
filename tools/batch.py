from enum import Enum, IntEnum
from timeit import default_timer as timer
import traceback
from collections import Counter


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


class Job:

    def __init__(self, i, batch):
        self.i = i
        self.batch = batch
        self.log = []
        self.id = ""
        self.result = None
        self.success = JobSuccess.SUCCESS
        self.is_debug = batch.is_debug
        self.is_dry_run = batch.is_dry_run
        self.is_bugreport = batch.is_bugreport
        self.committer = None

    @property
    def context(self):
        return self.batch.context

    def get_str(self, target_level=LogLevel.WARN):
        logs = "\n"+"\n".join(f"{level.name}: {msg}" for (level, msg) in self.log if level >= target_level)
        logs = logs.replace("\n", "\n    ")  # Indent all lines equally, even if the log message include line breaks
        return f"JOB-{self.i}: '{self.id}'->{self.success.name}{logs}\n"

    def __str__(self):
        return self.get_str()

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


class Batch:

    def __init__(self, name, level=LogLevel.WARN, dry_run=True, bugreport=False, no_metadata=False, **kwargs):
        self.name = name
        self.level = level
        self.context = kwargs
        self.jobs = []
        self.is_bugreport = bugreport
        self.is_debug = (level is LogLevel.DEBUG or bugreport)
        self.is_dry_run = dry_run
        self.no_metadata = no_metadata

    def process(self, generator, job_func):
        self.start = timer()
        if self.is_dry_run:
            print(f"DRY RUN")
        if self.is_debug:
            print(f"DEBUG")
        for i, data in enumerate(generator):
            job = Job(i, self)
            self.jobs.append(job)
            try:
                job.result = job_func(job, data)
            except Exception as e:
                if self.is_debug:
                    job.error(traceback.format_exc())
                else:
                    job.error(e)

            if job.success is not JobSuccess.SKIP:
                print(job.get_str(self.level))
        self.end = timer()
        self.elapsed = self.end-self.start
    
    def commit(self):
        for job in self.jobs:
            if job.committer:
                job.committer()

    def cur_job(self):
        return self.jobs[-1] if len(self.jobs) else None

    def summary_str(self):
        counts = Counter(job.success for job in self.jobs)
        rv =    f"---------------------\n"\
                f"Summary '{self.name}{' DRY RUN' if self.is_dry_run else ''}{' DEBUG' if self.is_debug else ''}\n"\
                f"SUCCESS {counts[JobSuccess.SUCCESS]} job(s)\n"\
                f"WARN    {counts[JobSuccess.WARN]} job(s)\n"\
                f"FAIL    {counts[JobSuccess.FAIL]} job(s)\n"\
                f"SKIP    {counts[JobSuccess.SKIP]} job(s)\n"\
                f"---------------------\n"\
                f"TOTAL   {len(self.jobs)} job(s)\n"\
                f"Elapsed time: {self.elapsed:.2f}s"
        return rv
