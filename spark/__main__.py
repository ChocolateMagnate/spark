#!/usr/bin/env python3
import argparse
import platform
import sys
import tomllib

import codes
from project import init_new_project
from lib import perror

SPARK_MINIMAL_PYTHON_VERSION = "3.10.0"


def load_sparkfile() -> dict:
    try:
        with open("Spark.toml", 'r') as sparkfile:
            return tomllib.loads(sparkfile.read())
    except OSError as e:
        perror("can't open Spark.toml", e, codes.EXIT_SPARKFILE_UNAVAILABLE)


def main(argv: list[str]) -> None:
    if platform.python_version() < SPARK_MINIMAL_PYTHON_VERSION:
        sys.stderr.write("spark: You are running Spark in an unsupported version of Python. Spark requires " +
                         "Python " + SPARK_MINIMAL_PYTHON_VERSION + " and you are running Python " +
                         platform.python_version() + ".")
        sys.exit(codes.EXIT_UNSUPPORTED_PYTHON_VERSION)

    parser = argparse.ArgumentParser(prog="spark", description="A declarative build system for C and C++ projects")
    parser.add_argument("--new", dest="title", type=str, help="Specifies the name of new Spark project to create.")
    args = parser.parse_args(argv)
    if args.title:
        init_new_project(args.title)

    spark_build_declaration: dict = load_sparkfile()


if __name__ == "__main__":
    argv = sys.argv
    argv.pop(0)  # The first argument in sys.argv is the file the Python Interpreter was called upon that we don't need.
    main(argv)
