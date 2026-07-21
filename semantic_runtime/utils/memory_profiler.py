import tracemalloc
import os
import psutil

class MemoryProfiler:
    @staticmethod
    def snapshot(label: str):
        current, peak = tracemalloc.get_traced_memory()
        process = psutil.Process(os.getpid())
        rss = process.memory_info().rss / (1024 * 1024 * 1024)  # GB

        print(f"\n[MEM CHECKPOINT: {label}]")
        print(f"  RSS Usage : {rss:.2f} GB")
        print(f"  Tracemalloc Current: {current / 10**6:.2f} MB")
        print(f"  Tracemalloc Peak   : {peak / 10**6:.2f} MB")

        # Take a snapshot to analyze later
        #snapshot = tracemalloc.take_snapshot()
        #top_stats = snapshot.statistics('lineno')

        #print(f"  Top 5 allocation sources:")
        #for stat in top_stats[:5]:
        #    print(f"    {stat}")