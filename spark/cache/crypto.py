from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from spark.destinations import get_public_cache_key_path


def generate_key_pair() -> tuple[bytes, RSAPrivateKey]:
    """Generates a pair of public and private cryptographic keys to be used to sign cache file.
    :return A tuple of bytes where the first element is the public key and the second one is private key."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend(),
    )
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    with open(get_public_cache_key_path(), 'wb') as public_key_file:
        public_key_file.write(public_key_bytes)

    return public_key_bytes, private_key


def stringify_private_key(private_key: RSAPrivateKey) -> str:
    """Converts an RSA private key into a PEM-encoded string. It's suitable to be
       stored within secure keychains and can be converted back using parse_private_key_string().
       :param private_key The RSAPrivateKey object to stringify.
       :return The PEM string for the private key."""
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()


def parse_private_key_string(private_key_pem: str) -> RSAPrivateKey:
    """Converts the given private key as a string into a proper RSAPrivateKey object.
       This function arises when storing the private key in a keyring where it must be
       serialised back and on. Thankfully, the private key string contains enough information
       to construct it into an RSAPrivateKey object.
       :param private_key_pem The string containing the private key.
       :return The functioning PRSAPrivateKey object initialised from the string."""
    return serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None,
        backend=default_backend()
    )


def sign(payload: bytes, private_key: RSAPrivateKey) -> bytes:
    """Signs the payload with the specified private key. Upon completion, this operation produces a signature,
    which is a sequence of bytes that encodes the signed data with the secured private key. WARNING: if private
    key was to be compromised, a malicious actor could not only read but also tamper with the signed data, therefore
    we do not store the private key, especially since it's only for a temporary file. Private keys, however, are
    cryptographically connected with their public counterpart, and while it's safe to store and expose public keys,
    cryptographic algorithms can verify if signature was signed with the private key with a public key. On practice,
    to ensure that the content was not changed since we wrote to it, we simply store the payload alongside the
    signature and verify it before decoding the contents.
    :param payload The data serialised as bytes to sign. For caching purpose, it is the pickled cache we want to secure.
    :param private_key The private key to sign the data with.
    :return The signature as bytes. It should be stored alongside the main payload to be able to verify authenticity.
    """
    return private_key.sign(
        payload,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )


def verify(payload: bytes, signature: bytes, public_key: bytes) -> bool:
    """Verifies the signature for the payload.
    :param payload The data that needs to be verified to be authentic.
    :param signature The signature passed alongside with the payload.
    :param public_key The public key bytes to verify with. The key must be cryptographically connected
    with the private key and be generated as a single pair for verification to be successful.
    :return True if signature is valid and False otherwise."""
    try:
        public_key = load_pem_public_key(public_key, default_backend())
        public_key.verify(
            signature, payload,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        # The public_key.verify method above would raise an exception if signature
        # is incorrect and silently return if it is correct.
        return True
    except InvalidSignature:
        return False
