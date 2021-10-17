from cProfile import Profile
import pstats
import functools
from typing import List
from mongoengine import queryset
from mongoengine.queryset.queryset import QuerySet
from sentry_sdk import start_span


def profile():
    profiler = Profile()

    def decorator(fn):
        def inner(*args, **kwargs):
            result = None
            try:
                result = profiler.runcall(fn, *args, **kwargs)
            finally:
                stats = pstats.Stats(profiler)
                stats.dump_stats(fn.__name__ + ".pstats")
                # stats.strip_dirs().sort_stats(*sort_args).print_stats(*print_args)
            return result

        return inner

    return decorator


def query_representation(query: QuerySet, aggregation: List = None):
    # Doesn't currently include _hint, _collation and _batch_size
    s = ""
    if query._collection:
        s += f"db.getCollection('{query._collection.name}')"
    if aggregation:
        s += f".aggregate({aggregation})"
    else:
        if query._query:
            s += f".find({query._query})"
        if query._ordering:
            s += f".sort({dict(query._ordering)})"
        if query._skip:
            s += f".skip({query._skip})"
        if query._limit:
            s += f".limit({query._limit})"
        if query._comment:
            s += f".comment({query._comment})"
    return s


def sentry_span(op, desc):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Do something before
            span = start_span(op=op, description=desc)
            value = func(*args, **kwargs)
            # Do something after
            span.finish()
            return value

        return wrapper

    return decorator
