import os.path
import tomllib
from pathlib import Path

import toml
import git


def get_project_author() -> str:
    """Analyses user environment to find relevant personal information to autofill the package.authors field.
    :return A string that represents the user personal information, such as their name and/or email."""
    repository = git.Repo(search_parent_directories=True)
    gitconfig: git.GitConfigParser = repository.config_reader()
    email = gitconfig.get_value("user", "email")
    username = gitconfig.get_value("user", "name")
    if username is not None and email is not None:
        return f"{username} <{email}>"
    USER: str = os.environ["USER"]
    return USER


def get_default_project_template(project_name: str, version: str, authors: list[str]) -> dict:
    """Generates a dictionary for the initial Spark.toml file that would later be converted into a
    TOML file at the root of the new project's directory.
    :param project_name The name of the project.
    :param version The initial version of the project.
    :param authors The array of first contributors.
    :return The dictionary with pre-populated template."""
    return {
        "package": {
            "name": project_name,
            "version": version,
            "license": "Your project license: MIT/Apache/GPL/etc.",
            "description": "Your project description here",
            "authors": authors
        }
    }


def init_new_project(project_name: str) -> None:
    os.makedirs(project_name, exist_ok=True)
    template: dict = get_default_project_template(project_name, "0.0.1-rc", [get_project_author()])
    sparkfile_destination = Path(project_name) / Path("Spark.toml")
    with open(sparkfile_destination, 'w') as sparkfile:
        toml.dump(template, sparkfile)
    print("Successfully created " + project_name + " at " + os.getcwd() + "!")
