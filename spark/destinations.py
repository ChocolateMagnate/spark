import os
import sys
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
    USER: str = os.environ["USER"]
    if sys.platform.startswith("linux"):
        return Path(f"/tmp/spark.{USER}.cache")
    elif sys.platform.startswith("darwin"):
        # While macOS also has /tmp, the $TMPDIR is more preferred destination to place temporary files.
        TMPDIR: str = os.environ["TMPDIR"]
        return Path(f"{TMPDIR}/spark.{USER}.cache")
    elif sys.platform.startswith("win"):
        TEMP: str = os.environ["TEMP"]
        return Path(f"{TEMP}/spark.{USER}.cache")


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
