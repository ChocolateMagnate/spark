#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from spark.codes import EXIT_TEE_NO_LOGFILE

EOF = b"__EOF__\n"


def main():
    """Emulates the Unix tee(1) command. We use it to be able to capture the standard output
       of build processes and write them to a log file, including any output child processes
       make. The provided solution is cross-platform and works by duplicating stdout and stderr
       to a shared pipe where processes are writing to and the tee.py process reads from it,
       writes the content to regular standard output and the log file as specified in the second
       command-line argument."""
    if len(sys.argv) < 2:
        sys.stderr.write("tee.py: output argument not specified.\n")
        sys.exit(EXIT_TEE_NO_LOGFILE)
    log_path = Path(sys.argv[1])
    if not log_path.exists():
        os.makedirs(log_path.parent, exist_ok=True)
    with open(log_path, "wb") as log:
        for line in sys.stdin.buffer:
            if line == EOF:
                break
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
            log.write(line)


if __name__ == "__main__":
    main()
