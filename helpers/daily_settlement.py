from datetime import datetime, UTC
from helpers.database.redis import get as get_redis


async def settle_user_active_coins(db, uid: str) -> float:
    """
    Settles accumulated interaction time from WebSocket pings.
    4 coins per 3600 seconds (1 hour) of active time.
    Returns earned coins rounded to 2 decimal places.
    """
    redis = get_redis()
    today_str = datetime.now(UTC).strftime("%Y-%m-%d")

    # Find all active_sec keys for this user
    pattern = f"user:{uid}:active_sec:*"
    keys = await redis.keys(pattern)

    total_earned = 0.0

    for key in keys:
        key_str = key.decode() if isinstance(key, bytes) else key
        date_part = key_str.split(":")[-1]

        # Settle days prior to today
        if date_part != today_str:
            seconds_val = await redis.get(key)
            if seconds_val:
                try:
                    sec = float(seconds_val)
                    earned = round((sec / 3600.0) * 4.0, 2)
                    if earned > 0:
                        total_earned += earned
                except (ValueError, TypeError):
                    pass
            await redis.delete(key)

    if total_earned > 0:
        total_earned = round(total_earned, 2)
        table = db.get(table="Users")
        await table.update_one({"id": uid}, {"$inc": {"coins": total_earned}})

    return total_earned
