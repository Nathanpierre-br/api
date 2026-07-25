import json
from typing import List, Optional
from helpers.database.redis import get as get_redis


WS_CHANNEL_CMD = "ws:commands"






class ApiBroadcastType:
    RawSend: int = 0
    InviteChatPush: int = 101


async def send_ws_message(message: dict, uids: Optional[List[str]] = None, type: int | None = None):
    """
    uids=None -> for all users
    uids=[...] -> for selected
    """
    redis = get_redis()
    payload = {"message": message, "type": type if type is not None else ApiBroadcastType.RawSend}
    if uids is not None:
        payload["uids"] = uids
    await redis.publish(WS_CHANNEL_CMD, json.dumps(payload))