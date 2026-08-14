from fastapi import APIRouter, Response
from fastapi.responses import RedirectResponse

from objects.types import PlatformType
from services.updates import UpdateService

update = APIRouter()


@update.get("/update")
async def get_update(platform: str = PlatformType.ANDROID):
    return await UpdateService.manifest(platform)


@update.get("/app/{platform}/latest")
async def get_download(platform: str):
    url = (await UpdateService.manifest(platform)).get("url")

    if not url:
        return Response(status_code=404)
    
    return RedirectResponse(url, status_code=302)
