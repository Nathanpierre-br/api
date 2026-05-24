from typing import Optional

from helpers.database.redis import get


class CacheProcessor:
    """
    Processor for making and getting caches.
    """

    @staticmethod
    async def Make(
        key: str, value: str | bytes | int, prefix: str = "", expiring_after: int = None
    ) -> None:
        """
        Making cache of data by prefix+key.

        Prefix is empty by default and you can not provide it.
        """
        redis = get()
        await redis.set(prefix + key, value, expiring_after)

    @staticmethod
    async def Update(
        key: str,
        value: str | bytes | int = None,
        prefix: str = "",
        expiring_after: int = None,
        keep_ttl: bool = False,
        increment: bool = False,
    ) -> None:
        """
        Making cache of data by prefix+key.

        Prefix is empty by default and you can not provide it.
        """
        redis = get()
        if increment:
            await redis.incr(prefix + key)
            return
        if value is None and expiring_after is not None:
            await redis.expire(prefix + key, expiring_after)
            return
        await redis.set(prefix + key, value, expiring_after, xx=True, keep_ttl=keep_ttl)

    @staticmethod
    async def Get(key: str, prefix: str = "") -> Optional[dict]:
        """
        None if there is no cache by provided key and prefix,
        "any" type when there is something.
        """
        redis = get()
        if key.startswith(prefix):
            key = key[len(prefix) :]
        return await redis.get(prefix + key)

    @staticmethod
    async def Delete(key: str, prefix: str = "") -> Optional[int]:
        """
        returning amount of deleted keys
        """
        redis = get()
        return await redis.unlink(prefix + key)
