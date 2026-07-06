from helpers.database.redis import get as get_redis


async def check_and_increment_tipping_limit(uid: str) -> tuple[bool, int]:
    """
    Checks if a user is tipping-blocked, or if they reached 10 tips in 5 minutes.
    Returns: (is_blocked: bool, ttl_remaining_seconds: int)
    """
    redis = get_redis()

    blocked_key = f"tipping_blocked:{uid}"
    ttl = await redis.ttl(blocked_key)
    if ttl > 0 or await redis.exists(blocked_key):
        return True, max(ttl, 86400)

    count_key = f"tipping_count:{uid}"
    current_count = await redis.incr(count_key)

    if current_count == 1:
        await redis.expire(count_key, 300)  # 5 minutes window

    if current_count >= 10:
        # Lock for 24 hours (86400 seconds)
        await redis.set(blocked_key, "1", ex=86400)
        await redis.delete(count_key)
        return True, 86400

    return False, 0





