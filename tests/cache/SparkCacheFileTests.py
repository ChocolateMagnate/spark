import os
import pickle
import tomllib
from pathlib import Path

import pytest
import toml
import keyring as kr

from spark import codes
from spark import destinations
from spark.cache import crypto
from spark.cache import SparkCacheFile

CACHE_PATH = destinations.get_temporary_cache_path()


def delete_cache_if_exists():
    if os.path.exists(CACHE_PATH):
        os.remove(CACHE_PATH)


def test_regenerate_cache():
    delete_cache_if_exists()
    with SparkCacheFile() as cache:
        assert cache.read() is not None


def test_signature_insertion():
    delete_cache_if_exists()
    with SparkCacheFile() as cache:
        pass
    with open(destinations.get_public_cache_key_path(), "rb") as public_key_file:
        public_key = public_key_file.read()
    with open(CACHE_PATH, "rb") as cache_file:
        contents = cache_file.read()
        signature = contents[:crypto.SIGNATURE_SIZE_BYTES]
        payload = contents[crypto.SIGNATURE_SIZE_BYTES:]
    assert crypto.verify(payload, signature, public_key)


def test_writeback_and_depickling():
    original_payload = {"key1": "value1", "key2": 3, "key3": [8, "value3"]}
    with SparkCacheFile(clear=True) as cache:
        cache.write(original_payload)
    with SparkCacheFile() as cache:
        received_payload = cache.read()
    assert received_payload == original_payload


def test_append_payload():
    delete_cache_if_exists()
    with SparkCacheFile() as cache:
        defaults = cache.read()
        defaults_size = cache.get_cache_size()
        additional_payload = ["clang++", "-D_GNU_SOURCE", "-fno-exceptions", "-flto", "main.cc", "-o", "main"]
        additional_payload_size = cache.append(additional_payload)
    with SparkCacheFile() as cache:
        actual_defaults = cache.read(defaults_size)
        actual_additional_payload = cache.read(additional_payload_size, defaults_size)
    assert actual_defaults == defaults
    assert additional_payload == actual_additional_payload


def test_sync():
    delete_cache_if_exists()
    with SparkCacheFile() as cache:
        payload = ["gcc", "main.c", "-o", "main", "-lcheck"]
        cache.write(payload)
        cache.sync()
        with open(destinations.get_temporary_cache_path(), "rb") as cache_file:
            contents = cache_file.read()
            synced_payload = contents[crypto.SIGNATURE_SIZE_BYTES:]
            assert pickle.dumps(payload) == synced_payload


def test_sync_regenerates_key_pair_if_does_not_exist():
    with open(destinations.get_public_cache_key_path(), "r") as public_key_file:
        public_key = public_key_file.read()
    with SparkCacheFile() as cache:
        service = cache.service
        username = cache.username
    kr.delete_password(service, username)
    with SparkCacheFile() as cache:
        pass
    with open(destinations.get_public_cache_key_path(), "r") as public_key_file:
        regenerated_public_key = public_key_file.read()
    # Public keys must be cryptographically bonded with their private counterpart, hence
    # deleting the private key must regenerate the whole pair and save a new public key.
    assert public_key != regenerated_public_key


def test_regenerate_fails_without_spark_toml():
    Spark = Path("Spark.toml")
    os.makedirs(".tmp", exist_ok=True)
    Spark.rename(".tmp/Spark.toml")
    with pytest.raises(SystemExit) as mock_exit:
        with SparkCacheFile() as cache:
            pass
    assert mock_exit.value.code == codes.EXIT_SPARKFILE_UNAVAILABLE
    Path(".tmp/Spark.toml").rename("Spark.toml")


def test_regenerates_successfully():
    with open("Spark.toml", "r+") as sparkfile:
        contents = tomllib.loads(sparkfile.read())
        contents["package"]["name"] = "Spark++"
    with open("Spark.toml", "w") as sparkfile:
        toml.dump(contents, sparkfile)
    with SparkCacheFile() as cache:
        contents = cache.read()
        assert contents["package"]["name"] == "Spark++"


def test_regenerate_cache_directory():
    delete_cache_if_exists()
    cache_directory: Path = destinations.get_temporary_cache_path().parent
    os.removedirs(cache_directory)
    with SparkCacheFile() as cache:
        assert cache_directory.exists()


def test_is_cached_if_opened():
    delete_cache_if_exists()
    with SparkCacheFile() as cache:
        cache_status = cache.is_cached()
        assert cache_status


def test_is_cached_after_sync():
    delete_cache_if_exists()
    with SparkCacheFile() as cache:
        pass
    with SparkCacheFile() as cache:
        cache_status = cache.is_cached()
        assert cache_status
