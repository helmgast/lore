from cProfile import Profile
import pstats


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
