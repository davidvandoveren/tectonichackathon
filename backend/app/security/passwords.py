import hashlib
import hmac
import secrets

_SCRYPT_PARAMS = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT_PARAMS)
    return digest, salt


def verify_password(password: str, expected_hash: bytes, salt: bytes) -> bool:
    candidate, _ = hash_password(password, salt)
    return hmac.compare_digest(candidate, expected_hash)
