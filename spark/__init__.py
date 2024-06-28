from pathlib import Path

import spark.destinations

# The list of all build files needed to construct the configuration.
SPARK_BUILD_DECLARATION_FILES = [destinations.get_environment_file_path(),
                                 destinations.get_user_preferences_file_path(),
                                 Path("spark.patch.toml"), Path("Spark.toml")]
