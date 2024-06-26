import os
import sys
import getpass
import hashlib
from pathlib import Path


def get_public_cache_key_path() -> Path:
    HOME: str = os.environ["HOME"]
    if sys.platform.startswith("linux"):
        return Path(HOME) / ".local" / "share" / "spark.public-key.pem"
    elif sys.platform.startswith("darwin"):
        return Path(HOME) / "Library" / "Application Support" / "spark.public-key.pem"
    elif sys.platform.startswith("win"):
        APPDATA: str = os.environ["APPDATA"]
        return Path(APPDATA) / "spark.public-key.pem"


def get_temporary_cache_path() -> Path:
    f"""Retrieves the path to the current cache file. Spark indexes different projects as absolute
       paths from the current working directory and constructs a hash for them stored in the 
       spark.USER.cache directory."""
    TMP: str = "/tmp"
    USER: str = getpass.getuser()
    project_file_hash: str = hashlib.sha512(os.getcwd().encode()).hexdigest()
    if sys.platform.startswith("darwin"):
        # While macOS also has /tmp, the $TMPDIR is more preferred destination to place temporary files.
        TMP = os.environ["TMPDIR"]
    elif sys.platform.startswith("win"):
        TMP = os.environ["TEMP"]
    return Path(TMP) / f"spark.{USER}.cache" / project_file_hash


def get_user_preferences_file_path() -> Path:
    """Obtains the path to the user-specific configuration file. Spark expects it to define preferred
    toolchain and default options, such as the use of PCH, ramdisk and global caching."""
    HOME: str = os.environ["HOME"]
    if sys.platform.startswith("linux"):
        return Path(HOME) / ".config" / "spark.preferences.toml"
    elif sys.platform.startswith("darwin"):
        return Path(HOME) / "Library" / "Preferences" / "spark.preferences.toml"
    elif sys.platform.startswith("win"):
        LOCALAPPDATA: str = os.environ["LOCALAPPDATA"]
        return Path(LOCALAPPDATA) / "spark.preferences.toml"


def get_environment_file_path() -> Path:
    """Obtains the path to the global system-wide metadata file. It is expected that it should include
    information about the machine running Spark (such as CPU details) and include a default toolchain."""
    if sys.platform.startswith("linux"):
        return Path("/etc/spark.environment.toml")
    elif sys.platform.startswith("darwin"):
        return Path("/Library/Preferences/spark.environment.toml")
    elif sys.platform.startswith("win"):
        return Path("C:\\ProgramData\\spark.environment.toml")
