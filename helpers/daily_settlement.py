from datetime import datetime, UTC, timedelta
from helpers.database.redis import get as get_redis
from fastapi import Request


CHECKIN_COIN_REWARDS = [1.0, 2.0, 3.0, 10.0]
CHECKIN_COIN_WEIGHTS = [0.50, 0.30, 0.15, 0.05]

LOTTERY_REWARDS = [2.0, 5.0, 10.0]
LOTTERY_WEIGHTS = [0.40, 0.30, 0.20, 0.09, 0.01]

REP_CAP = 20


def local_date(tz_minutes: int) -> datetime:
    return datetime.now(UTC) + timedelta(minutes=tz_minutes)


def date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def earned_rep(streak: int) -> int:
    return min(1 + streak, REP_CAP)


async def get_tz(request: Request) -> int:
    try:
        body = await request.json()
        return int(body.get("timezone", 0))
    except Exception:
        return 0








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
