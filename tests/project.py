import os.path

from spark.project import *


def test_init_new_default_project():
    project_name = "Spark"
    init_new_project(project_name)
    assert os.path.isdir(project_name)
    sparkfile = Path(project_name) / Path("Spark.toml")
    assert os.path.isfile(sparkfile)
    payload = tomllib.loads(sparkfile.open().read())
    assert payload["package"]["name"] == "Spark"
    assert payload["package"]["version"] == "0.0.1-rc"
