import os
import sys

import installers


def perror(message: str, exception: OSError, code: int = 0) -> None:
    """Pythonic analogue of the C perror(3) function. It provides a simple way to print error
    messages along with human-readable errno variable. It is a common way how errors are printed
    in Unix-like operating systems and Spark joins a shared convention with a number of other
    command line utilities that follow this convention.
    :param message The error message to print to standard error stream.
    :param exception The OSError exception object that raised the error. perror(3) is commonly
    only used with operating system related errors, and so far we will continue this convention.
    :param code (optional) The error code. If the error is fatal, and we cannot continue after it,
    supply any error code and the function will exit with it."""
    errno: int = exception.errno
    errno_message: str = os.strerror(errno)
    sys.stderr.write("spark: " + message + ": " + errno_message + '\n')
    if code != 0:
        sys.exit(code)
