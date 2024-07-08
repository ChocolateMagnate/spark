import os
import shutil
import subprocess as sb
import string
import random
import sys
import time
from pathlib import Path

from spark import codes
from spark.lib import tee

PYTHON_EXECUTABLE = sys.executable or shutil.which("python3")


def test_error_if_no_output_file():
    tee_process = sb.run([PYTHON_EXECUTABLE, tee.__file__])
    assert tee_process.returncode == codes.EXIT_TEE_NO_LOGFILE


def test_create_directories():
    letters = string.ascii_lowercase
    directory = ''.join(random.choice(letters) for _ in range(15))
    parents = [Path(parent) for parent in directory.split('a')]
    path = Path()
    for parent in parents:
        path /= parent
    path /= "output.log"
    tee_process = sb.run([PYTHON_EXECUTABLE, tee.__file__, path])
    assert path.exists()
    assert tee_process.returncode == 0
    shutil.rmtree(path.parent)


def test_output_logfile():
    LOG1 = b"This should be logged to the output.log file from tee.py.\n"
    LOG2 = b"Even more output that goes through tee.py.\n"
    pipe_read_fd, pipe_write_fd = os.pipe()
    os.write(pipe_write_fd, LOG1)
    tee_process = sb.Popen([PYTHON_EXECUTABLE, tee.__file__, "output.log"], stdin=pipe_read_fd)
    time.sleep(1)
    with open("output.log", "rb") as logfile:
        assert logfile.read() == LOG1
    os.write(pipe_write_fd, LOG2)
    time.sleep(1)
    with open("output.log", "rb") as logfile:
        combined_contents = LOG1 + LOG2
        assert logfile.read() == combined_contents
    tee_process.terminate()
    tee_process.wait()
    os.remove("output.log")
