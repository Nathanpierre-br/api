from orjson import dumps
from websockets.asyncio.client import connect

from .config import Config


async def send_admin_ws(victims: list | str, payload: dict | str):
    if isinstance(victims, str) and victims != "ALL":
        raise Exception("Invalid victims")

    headers = {
        "WS-ADMIN-KEY": Config.WS_ADMIN_KEY,
        "WS-ADMIN-VERIFY": Config.WS_ADMIN_VERIFY,
    }
    url = Config.WS_LINK
    request = dumps({"ADMIN-SAYS": {"VICTIMS": victims, "WEAPON": payload}}).decode()
    async with connect(url, additional_headers=headers) as websocket:
        await websocket.send(request)
        response = await websocket.recv()
        print(response)
        return response
