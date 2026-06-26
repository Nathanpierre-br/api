from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.routers.cachable import CachableRoute
from objects import Base, Errors


altteam = APIRouter()
altteam.route_class = CachableRoute



@altteam.get("/g/s/altteam")
@altteam.get("/x{ndcId}/s/altteam")
async def storesections_mock(request: Request, ndcId: int = 0):
    return Base.Answer()