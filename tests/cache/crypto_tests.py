import pickle

import keyring as kr
from cryptography.hazmat.primitives import serialization

from spark.cache import crypto
from spark.destinations import get_public_cache_key_path


def test_generate_key_pair():
    supplied_public_key, private_key = crypto.generate_key_pair()
    verified_public_key = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    assert supplied_public_key == verified_public_key


def test_save_public_key():
    generated_public_key, private_ley = crypto.generate_key_pair()
    with open(get_public_cache_key_path(), "rb") as saved_public_key:
        assert generated_public_key == saved_public_key.read()


def test_save_private_key():
    generated_public_key, private_key = crypto.generate_key_pair()
    original_private_key_string = crypto.stringify_private_key(private_key)
    kr.set_password("crypto.service", "user", original_private_key_string)
    provided_private_key_string = kr.get_password("crypto.service", "user")
    assert provided_private_key_string == original_private_key_string


def test_verify_payload():
    payload = {
        "package": {
            "name": "ImageBuilder",
            "version": "2.3.5",
            "license": "MIT",
            "authors": ["Andrew Sweet <andrew-sweet@gmail.com", "Nikolas Tree <nictree@protonmail.com"],
            "description": "A simple and intuitive to use library for dynamically creating pictures"
        },
        "dependencies": {
            "fmt": "^2.3.4",
            "ImageMagick": "^7.1.1"
        },
        "dev-dependencies": {
            "check": {
                "version": "^0.32",
                "macro": "LIBCHECK"
            }
        },
        "image-builder": {
            "sources": "src/builder/**",
            "lto": "thin",
            "strip": "all-unneeded"
        }
    }
    payload_bytes: bytes = pickle.dumps(payload)
    public_key_bytes, private_key = crypto.generate_key_pair()
    signature: bytes = crypto.sign(payload_bytes, private_key)
    assert crypto.verify(payload_bytes, signature, public_key_bytes)
