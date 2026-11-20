"""Process RSS in MB: psutil if installed, else /proc (Linux), else peak RSS from resource."""
import os
import sys


def rss_mb():
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        pass
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024
    except OSError:
        pass
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024
    except ImportError:
        return None


def process_start_epoch():
    try:
        import psutil
        return psutil.Process(os.getpid()).create_time()
    except ImportError:
        return None
