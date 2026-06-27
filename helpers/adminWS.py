import json
from typing import List, Optional
from helpers.database.redis import get as get_redis


WS_CHANNEL_CMD = "ws:commands"


async def send_ws_message(message: dict, uids: Optional[List[str]] = None):
    """
    uids=None -> for all users
    uids=[...] -> for selected
    """
    print(f"sending data for ws for {uids}")
    redis = get_redis()
    payload = {"message": message}
    if uids is not None:
        payload["uids"] = uids
    await redis.publish(WS_CHANNEL_CMD, json.dumps(payload))