from hashlib import blake2b


class Blake:
    """
    Blake2b hash wrapper to easily hash data with optional key and salt.
    """

    def __init__(
        self,
        data: str | bytes,
        key: str | bytes = b"",
        salt: str | bytes = b"",
        digest_size: int = 64,
    ):
        if isinstance(data, str):
            data = data.encode("utf-8")
        if isinstance(key, str):
            key = key.encode("utf-8")
        if isinstance(salt, str):
            salt = salt.encode("utf-8")
        self._hash = blake2b(
            data, key=key, salt=salt, digest_size=digest_size
        ).hexdigest()

    @property
    def hash(self):
        return self._hash
