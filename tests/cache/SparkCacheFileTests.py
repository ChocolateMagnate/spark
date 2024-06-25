import os
import pickle

from spark import destinations
from spark.cache import crypto, SIGNATURE_SIZE_BYTES
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
        signature = contents[:SIGNATURE_SIZE_BYTES]
        payload = contents[SIGNATURE_SIZE_BYTES:]
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

