from os import urandom

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from helpers.config import Config


class _Aether:
    """
    AES-128 / AES-192 / AES-256 encryption facade singleton.
    """

    def __init__(self, key_bits: int = 256, key: bytes | str | None = None):
        if key_bits not in (128, 192, 256):
            raise ValueError("Invalid AES key length.")

        if key is not None:
            self.key = key if isinstance(key, bytes) else key.encode()
        else:
            self.key = urandom(key_bits // 8)

        self.cipher = Cipher(algorithms.AES(self.key), modes.ECB())

    def encrypt(self, data: bytes | str) -> bytes:
        if isinstance(data, str):
            data = data.encode()

        padder = padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()

        encryptor = self.cipher.encryptor()
        return encryptor.update(padded_data) + encryptor.finalize()

    def decrypt(self, data: bytes) -> bytes:
        decryptor = self.cipher.decryptor()
        decrypted_padded = decryptor.update(data) + decryptor.finalize()

        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(decrypted_padded) + unpadder.finalize()


Aether = _Aether(key=Config.AETHER_KEY)
