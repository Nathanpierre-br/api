from fastapi import APIRouter, Response

from services.repository import RepositoryService

repository = APIRouter()


@repository.get("/repo/{kind}")
async def get_feed(kind: str):
    feed = await RepositoryService.feed(kind)
    if feed is None:
        return Response(status_code=404)
    return feed
