import os
import sys
import pickle
import tomllib
import getpass
from pathlib import Path
from typing import Self, Any

import keyring as kr

from spark import SPARK_BUILD_DECLARATION_FILES
from spark import codes
from spark import destinations
from spark.cache import crypto
from spark.destinations import get_temporary_cache_path, get_public_cache_key_path

# The cache files can only be accessed by the owner. The permission mask includes the execute bit
# because various Unix-based filesystems require the user to have the execute permission to create
# new files in it. For more details, refer to https://askubuntu.com/a/1244013.
OWNER_READ_AND_WRITE_ONLY_PERMISSION_MASK: int = 0o700


class SparkCacheFile:
    """Spark cache file that encapsulates pre-processed data to avoid parsing and reading all
       build declaration files every time Spark is invoked. Currently, there are 4 files Spark
       needs to read to make sure it formulated the build configuration:
    1. Spark.toml (local per project)
    2. spark.patch.toml (local per project)
    3. spark.preferences.toml (local per user)
    4. spark.environment.toml (global per system)
       Caching allows to process these files once, save them to the cache file and read it instead.
       Spark uses the `pickle` module to serialise the data and stores it in the temporary directory
       named spark.${USER}.cache where $USER is the currently logged-in user. This directory contains
       files per each project (that being a directory with the Spark.toml file at its root) whose
       cache file is computed as the SHA512 hash of the current directory. As an example, if Spark
       is invoked from the directory /home/sophia/programming-projects/wisengine, its hash will be:
       >> hashlib.sha512(b"/home/sophia/programming-projects/wisengine").hexdigest()
       'bf328384a3d54da4908ad2d75b69bdb7864166d0b80c27c77f7b42ad559f25bf0cea69fb13b4c24c64aeceea479571b1f921334ae14b08fe20cace6320ba1041'"""

    def __init__(self, clear: bool = False):
        self.cache = b''
        self.clear = clear
        self.signature = b''
        self.public_key_bytes = b''
        self.username: str = getpass.getuser()
        self.service = f"spark.{self.username}.cache"
        self.path: Path = get_temporary_cache_path()
        self.opened: bool = False

    def __enter__(self) -> Self:
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __load_public_key(self) -> bytes:
        """Loads an existing public key or generates a new one if it doesn't exist."""
        public_key_path: Path = get_public_cache_key_path()
        if not public_key_path.exists():
            public_key_bytes, private_key = crypto.generate_key_pair()
            kr.set_password(self.service, self.username, crypto.stringify_private_key(private_key))
            with open(get_public_cache_key_path(), "wb") as public_key_file:
                public_key_file.write(public_key_bytes)
        else:
            with open(get_public_cache_key_path(), "rb") as public_key_file:
                public_key_bytes = public_key_file.read()
        return public_key_bytes

    def sync(self) -> None:
        """Writes the cache file back on the filesystem."""
        private_key_pem: str = kr.get_password(self.service, self.username)
        if private_key_pem is None:
            public_key_bytes, private_key = crypto.generate_key_pair()
            kr.set_password(self.service, self.username, crypto.stringify_private_key(private_key))
            with open(get_public_cache_key_path(), "wb") as public_key_file:
                public_key_file.write(public_key_bytes)
        else:
            private_key = crypto.parse_private_key_string(private_key_pem)
        self.signature = crypto.sign(self.cache, private_key)
        with open(self.path, "wb") as cache:
            cache.write(self.signature)
            cache.write(self.cache)

    def regenerate(self) -> None:
        """Reloads the cache by reading the build files normally and generating the cache for them.
           This is often the need if the cache file doesn't exit yet or was deleted. Upon completion
           of this operation, the cache file is up and ready to be read."""
        if not Path("Spark.toml").exists():
            sys.stderr.write("spark: can't open Spark.toml: No such file or directory")
            sys.exit(codes.EXIT_SPARKFILE_UNAVAILABLE)
        build = dict()
        for declaration in SPARK_BUILD_DECLARATION_FILES:
            if not declaration.exists():
                continue
            with open(declaration, "r") as declaration_file:
                parsed_declaration: dict[str, Any] = tomllib.loads(declaration_file.read())
                build = {**build, **parsed_declaration}
        self.cache = pickle.dumps(build)
        self.opened = True
        self.sync()  # We sync because we often expect an existing cache file to be available.

    def open(self) -> Self:
        self.opened = True
        self.public_key_bytes = self.__load_public_key()
        if not self.path.exists():
            os.makedirs(self.path.parent, OWNER_READ_AND_WRITE_ONLY_PERMISSION_MASK, True)
            self.regenerate()
            return self
        if self.clear:
            return self
        cache_file_modification_timestamp = os.path.getmtime(destinations.get_temporary_cache_path())
        for declaration in SPARK_BUILD_DECLARATION_FILES:
            if not declaration.exists():
                continue
            if os.path.getmtime(declaration) > cache_file_modification_timestamp:
                self.regenerate()
                return self
        with open(self.path, "rb") as cache:
            contents = cache.read()
            self.signature = contents[:crypto.SIGNATURE_SIZE_BYTES]
            self.cache = contents[crypto.SIGNATURE_SIZE_BYTES:]
            if not crypto.verify(self.cache, self.signature, self.public_key_bytes):
                self.regenerate()
        return self

    def close(self):
        self.sync()
        self.opened = False

    def is_cached(self) -> bool:
        """Checks if temporary cache file exists and is valid.
        :return True if there exists correctly signed cache file, and False otherwise."""
        if not self.opened:
            self.open()
        if crypto.verify(self.cache, self.signature, self.public_key_bytes):
            return True
            # Since the cache file didn't pass the verification check, it's best to delete it.
        os.remove(self.path)
        return False

    def write(self, data) -> None:
        """Overwrites the in-memory cache with the supplied data. It shall be pickled into a stram of bytes
           remain in memory until the cache file is either sync()ed or closed (happens automatically in the
           context manager). This method overwrites the cache because there is no way to reliably distinguish
           between bytes as meaningful data except for either pickling each request as an element of array or
           know the offsets ahead of time. Since cache files are often treated as a single meaningful unit,
           it makes more sense to read and write to it as so and if you need to add to cache, use append()."""
        self.cache = pickle.dumps(data)

    def append(self, data) -> int:
        """Appends the provided data to the cache. Normally, the cache file is treated as a single whole, and
           it's written to and read as a single coherent unit, but append() shall add the provided data to
           the existing cache as it is. When doing so, the caller will need to make sure you read the cache
           properly because de-pickling the whole cache file with default read() will become dangerous, but
           append() should only be used when you read by known byte offsets.
           :param data The payload to append to the cache file.
           :return The size of the provided data in bytes."""
        provision = pickle.dumps(data)
        self.cache += provision
        return len(provision)

    def read(self, size: int = None, offset: int = 0):
        """Reads the temporary cache data. It is generally faster to read and pickle a temporary file than
        opening a number of build files, parsing and assembling their settings, and therefore, if the temporary
        file exists, we always prefer to use it. Consult temporary.is_cached() to check if cache file exists.
        :param size (optional) The number of bytes to read. If unspecified, it reads the whole file.
        :param offset (optional) The byte offset from where to start de-pickling.
        :return De-pickled data from the cache file."""
        if not self.opened:
            raise FileNotFoundError(f"A file was tried to be read from {self.path.name} but it was not open! "
                                    f"Use the context manager: with SparkCacheFile() as cache")
        if not self.path.exists():
            self.regenerate()
        if self.is_cached() and size is not None:
            size += offset
            contents = self.cache[offset:size]
            return pickle.loads(contents)
        return pickle.loads(self.cache)

    def get_cache_size(self) -> int:
        """Returns the amount of bytes the cache holds at the moment."""
        return len(self.cache)
