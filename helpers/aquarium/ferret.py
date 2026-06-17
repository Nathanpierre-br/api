from cryptography.fernet import Fernet

from helpers.config import Config


class _Ferret:
    """
    Fernet encryption facade singleton.
    """

    def __init__(self, key: bytes | str | None = None):
        if key is None:
            key = Fernet.generate_key()

        if not isinstance(key, bytes):
            key = key.encode("utf-8")

        self._fernet = Fernet(key)

    def encrypt(self, data: bytes | str) -> bytes:
        if not isinstance(data, bytes):
            data = data.encode("utf-8")
        return self._fernet.encrypt(data)

    def decrypt(self, data: bytes) -> bytes:
        return self._fernet.decrypt(data)


Ferret = _Ferret(key=Config.FERNET_KEY)
