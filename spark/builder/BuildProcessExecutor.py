import os
import subprocess
import sys

from collections import deque
from typing import Self, Iterable

import psutil

from spark import codes
from spark.lib import perror


def get_recent_load_average() -> float:
    """Retrieves the load average for the last minute. On Unix-like operating systems, the
       kernel itself keeps trek of load average and could be retrieved with os.getloadavg(),
       but on Windows it is possible to manually compute it, but somewhat difficult to
       implement, especially since the process executor aims to minimise the amount of
       Python code executed in between process invocations. On Windows, this value is ignored.
       :return The load average on the last minute."""
    try:
        return os.getloadavg()[0]
    except OSError:
        return 0.0  # If load average couldn't be extracted, we just ignore it.


def handle_subcommand_failure() -> None:
    """Prints the error message if the builder process fails and exits."""
    sys.stderr.write("spark: subcommand failed.\n"
                     "\tThis is not an issue with Spark, but indicates the build process couldn't be\n"
                     "\tsuccessfully completed. Review the errors above and modify the source code or\n"
                     "\tthe Spark.toml configuration to reflect the proper solution. If you suspect the\n"
                     "\tbuild process is correct and it's Spark that doesn't pass the arguments properly,\n"
                     "\tplease report a bug at https://github.com/ChocolateMagnate/spark/issues.\n")
    sys.exit(codes.EXIT_SUBCOMMAND_FAILED)


class BuildProcessExecutor:
    """Asynchronous process executor. This executor is in a lot of ways reminiscent to concurrent.futures.
       ProcessPoolExecutor, however, it cannot be used to easily run a batch of builder jobs because
       ProcessPoolExecutor works with Pythonic code, which would result in wasting jobs number of
       threads just to keep forking and executing them. This implementation is provided to instead
       directly spawn builder jobs from the main Python thread and work with external commands."""

    def __init__(self, total: int, jobs: float = None, load_average: float = None, quiet: bool = False):
        """Initialises a new process executor.
           :param total The total number of build processes that will be executed by the executor.
           It's used in printing the counter of [current/total] steps, similarly to how Ninja does.
           :param jobs (optional) The number of parallel builder tasks (jobs) to run.
           Defaults to the number of threads on the host machine.
           :param load_average (optional) The maximum load average to balance. If load average in the
           las minute crosses this value, Spark will drop and run less builder processes to balance
           the load on the system. This value is ignored on Windows since there is no load average on it.
           :param quiet (optional) The flag whether to print the compiler commands executed. By default,
           it's disabled, which would print every command invoked by Spark, useful for a verity of purposes.
           When enabled, it would not print any of them, but still add them to the log file."""
        self.total = total
        self.jobs = jobs if jobs is not None else psutil.cpu_count()
        self.load_average = load_average if load_average is not None else self.jobs
        self.processes: dict[int, subprocess.Popen] = {}
        self.subcommands: deque[list[str]] = deque()
        self.running_jobs = self.jobs
        self.quiet = quiet
        self.counter = 0

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val: Exception, traceback: str):
        # If we didn't start tasks in the body of the context manager, we should start
        # them here and guarantee all tasks complete when the executor finishes.
        self.start()
        self.shutdown()
        # We ignore ValueError because it's caused by the caller submitting not valid subcommand.
        if exc_type is not None and exc_type != ValueError:
            handle_subcommand_failure()
            return True
        return False

    def submit(self, subcommand: list[str]) -> None:
        """Adds a new task to the executor. The new task starts asynchronously in a new child
           process, and a future associated with its result is returned.
           :param subcommand The list of command-line arguments to execute. The first argument should be
           executable, preferably its absolute path, followed optionally by arguments.
           Although optional, it's highly likely you will need them, since compilers/linkers/interpreters
           often rely on these arguments to tell all information they need. It is, however, possible to
           not specify this argument if the executable does not accept any arguments, such as ldconfig(8).
           This list should not contain the executable itself but only the arguments that come after it."""
        self.subcommands.appendleft(subcommand)

    def progress(self) -> tuple[int, int]:
        return self.counter, self.total

    def is_work_complete(self) -> bool:
        return not self.processes and not self.subcommands

    def start(self) -> None:
        """Spawns the builder processes to fill the vacant threads. This method will check the appropriate
           number of additional (vacant) processes that need to be spawned and log the subcommand invocation
           into the standard output."""
        if len(self.processes) > self.jobs:
            return

        loadavg: float = get_recent_load_average()
        self.running_jobs = 1 if loadavg > self.load_average else self.jobs

        available_subcommands = len(self.subcommands)
        vacant_process_difference = self.running_jobs - len(self.processes)
        additional_builder_jobs = vacant_process_difference \
            if vacant_process_difference <= available_subcommands else available_subcommands
        try:
            for _ in range(additional_builder_jobs):
                self.counter += 1
                subcommand: list[str] = self.subcommands.pop()
                process = subprocess.Popen(subcommand)
                self.processes[process.pid] = process
                log = f"[{self.counter}/{self.total}] {" ".join(subcommand)}"
                if not self.quiet:
                    print(log)
        except OSError as e:
            perror("subcommand could not be started", e, codes.EXIT_NO_SUCH_SUBCOMMAND)
            self.shutdown()

    def as_completed(self) -> Iterable[tuple[int, int]]:
        if not self.subcommands:
            return

        self.start()
        try:
            pid, status = os.waitpid(-1, 0)
            del self.processes[pid]
            # The status variable, depending on the OS, could include more information than just
            # the exit code. On Unix, it returns the mask where the lower 8 bits are the exit code,
            # and on Windows it returns the exit code only. To make it easier to extract the exit
            # code alone, on Windows os.waitpid() returns the status shifted by 8 bits so that you
            # could shift it back and get the exit code regardless of your OS. For more details, refer
            # to the Python documentation: https://docs.python.org/3/library/os.html#os.waitpid
            yield pid, status >> 8
        except ChildProcessError:
            return

    def shutdown(self) -> None:
        for pid, process in list(self.processes.items()):
            del self.processes[pid]
            process.terminate()
            process.wait()
