from typing import Optional, Union, Any

from helpers.database.redis import get


class CacheProcessor:

    @staticmethod
    def _norm(x: Union[str, bytes, None]) -> str:
        if x is None:
            return ""
        if isinstance(x, bytes):
            return x.decode("utf-8", errors="ignore")
        return str(x)

    @staticmethod
    async def Make(
        key: str,
        value: str | bytes | int,
        prefix: str = "",
        expiring_after: Optional[int] = None,
    ) -> None:
        if value is None:
            return

        redis = get()

        key = CacheProcessor._norm(key)
        prefix = CacheProcessor._norm(prefix)

        await redis.set(prefix + key, value, expiring_after)

    @staticmethod
    async def Update(
        key: str,
        value: str | bytes | int | None = None,
        prefix: str = "",
        expiring_after: Optional[int] = None,
        keep_ttl: bool = False,
        increment: bool = False,
    ) -> None:

        redis = get()

        key = CacheProcessor._norm(key)
        prefix = CacheProcessor._norm(prefix)

        full_key = prefix + key

        if increment:
            await redis.incr(full_key)
            return

        if value is None and expiring_after is not None:
            await redis.expire(full_key, expiring_after)
            return
        if value is None:
            return #idk

        await redis.set(full_key, value, expiring_after, keepttl=keep_ttl)

    @staticmethod
    async def Get(
        key: str | bytes,
        prefix: str = "",
    ) -> Optional[Any]:

        redis = get()

        key = CacheProcessor._norm(key)
        prefix = CacheProcessor._norm(prefix)

        return await redis.get(prefix + key)

    @staticmethod
    async def Delete(
        key: str,
        prefix: str = "",
    ) -> Optional[int]:

        redis = get()

        key = CacheProcessor._norm(key)
        prefix = CacheProcessor._norm(prefix)

        return await redis.unlink(prefix + key)
