import asyncio
import tomllib
from typing import Any

import aiofiles

from .destinations import get_user_preferences_file_path, get_environment_file_path


async def load_sparkfile_async():
    async with aiofiles.open("Spark.toml", 'r') as sparkfile:
        content: str = await sparkfile.read()
        return tomllib.loads(content)


async def load_preferences_async():
    async with aiofiles.open(get_user_preferences_file_path()) as preferences:
        content: str = await preferences.read()
        return tomllib.loads(content)


async def load_environment_async():
    async with aiofiles.open(get_environment_file_path()) as environment:
        content: str = await environment.read()
        return tomllib.loads(content)


async def load_spark_files() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Sources 3 configuration files: Spark.toml, spark.preferences.toml and spark.environment.toml.
    These files define the build settings used to compile the project.
    :return A tuple of 3 build declarations."""
    return await asyncio.gather(load_sparkfile_async(), load_preferences_async(), load_environment_async())


async def get_context():
    """Generates the final build configuration based on the provided environment. Spark will source 3 files
    in order: Spark.toml, user's spark.preferences.toml and global spark.environment.toml, and if a requested
    build option is not defined in one, it will cascade forward into the next one. These 3 separate declarations
    can be extracted with context.load_spark_files function, and this one mixes them together into a single dictionary.
    :return String key dictionary for viewing the build options to use."""
    spark, preferences, environment = await load_spark_files()
    context = spark.copy()
    for key, value in preferences.items():
        if key not in context:
            context[key] = value
    for key, value in environment.items():
        if key not in context:
            context[key] = value
    return context
