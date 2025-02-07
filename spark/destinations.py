import os
import sys
import getpass
import hashlib
from pathlib import Path
from datetime import datetime


def get_temporary_directory() -> Path:
    """Seeks the preferred destination for temporary files on the host system."""
    TMP: str = "/tmp"
    if sys.platform.startswith("darwin"):
        # While macOS also has /tmp, the $TMPDIR is more preferred destination to place temporary files.
        TMP = os.environ["TMPDIR"]
    elif sys.platform.startswith("win"):
        TMP = os.environ["TEMP"]
    return Path(TMP)


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
    """Retrieves the path to the current cache file. Spark indexes different projects as absolute
       paths from the current working directory and constructs a hash for them stored in the 
       spark.USER.cache directory."""
    USER: str = getpass.getuser()
    TMP: Path = get_temporary_directory()
    project_file_hash: str = hashlib.sha512(os.getcwd().encode()).hexdigest()
    return TMP / f"spark.{USER}.cache" / project_file_hash


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


def get_build_logging_path() -> Path:
    """Retrieves the path to the build log file where to log the build process.
       Spark logs all files to the user-specific spark.$USER.build directory inside each
       there is a separate directory per day and hour when built occurred, as well as the
       project name. This distinction helps to avoid polluting filenames, give additional
       information to users when the build started and is granular enough to avoid collisions.
       :return The path to the log file."""
    parts = Path(os.getcwd()).parts
    parent = parts[len(parts) - 1]
    HOME: str = os.path.expanduser("~")
    day, hour = datetime.now().strftime("%d.%m.%Y %H:%M").split()
    base_path = Path(HOME) / ".local" / "share" / "spark"
    if sys.platform.startswith("win"):
        base_path = Path(HOME) / "AppData" / "Local" / "spark" / "Logs"
    elif sys.platform.startswith("darwin"):
        base_path = Path(HOME) / "Library" / "Logs" / "spark"
    return base_path / day / hour / f"{parent}.log"
