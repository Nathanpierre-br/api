from Crypto.Cipher import Blowfish
from Crypto.Util.Padding import pad, unpad
from helpers.config import Config


class __FISH:
    def __init__(self):
        self.__size = Blowfish.block_size
        __key = pad(Config.FERNET_KEY.encode("utf8"), self.__size)
        __mode = Blowfish.MODE_ECB

        self.chef = Blowfish.new(__key, __mode)
        # self.customer = Blowfish.new(__key, __mode)

    def cook(self, raw_fish: str | bytes):
        return self.chef.encrypt(
            pad(
                raw_fish if isinstance(raw_fish, bytes) else raw_fish.encode(),
                self.__size,
            )
        )

    def eat(self, cooked_fish: str | bytes):
        return unpad(
            # self.customer.decrypt(
            self.chef.decrypt(
                cooked_fish if isinstance(cooked_fish, bytes) else cooked_fish.encode()
            ),
            self.__size,
        )


FISH = __FISH()
