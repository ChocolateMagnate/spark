import os
import pickle
import sys
from pathlib import Path
from crypto import verify
from ..destinations import get_temporary_cache_path, get_public_cache_key_path


def write(data) -> None:
    """Appends the supplied data into a temporary cache. In most systems, it's implemented as
    a temporary file that we use to avoid re-sourcing declaration files every time when we invoke
    Spark. As the result, the temporary files serves as the anchor we check beforehand and source
    all settings from there. Any additional writes would append to the file, and the method does
    not normalise the data into structural identity if it requires so.
    :param data The data to pickle in the temporary file."""
    with open(get_temporary_cache_path(), 'a') as cache:
        cache.write(pickle.loads(data))


def is_cached() -> bool:
    """Checks if temporary cache file exists and is valid.
    :return True if there exists correctly signed cache file, and False otherwise."""
    cache_file: Path = get_temporary_cache_path()
    if cache_file.exists():
        cache = cache_file.open("rb").read()
        signature = cache[:512]  # We use the RSA 4096-bit singing, which produces the 512 bytes we store at the start.
        payload = cache[512:]  # The rest of the file is populated with the payload.
        with open(get_public_cache_key_path(), "rb") as public_key_file:
            public_key_bytes = public_key_file.read()
        if verify(payload, signature, public_key_bytes):
            return True
    return False


def read():
    """Reads the temporary cache data. It is generally faster to read and pickle a temporary file than
    opening a number of build files, parsing and assembling their settings, and therefore, if the temporary
    file exists, we always prefer to use it. Consult temporary.is_cached() to check if cache file exists.
    :return De-pickled data from the cache file."""
    if is_cached():
        with open(get_temporary_cache_path()) as cache:
            return pickle.load(cache)
