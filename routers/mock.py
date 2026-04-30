from fastapi import APIRouter, Request
from time import time as timestamp

from objects import Errors, Base
from helpers.routers.cachable import CachableRoute

mock = APIRouter()
mock.route_class = CachableRoute


@mock.post("/x{ndcId}/s/community/stats/user-active-time")
async def count_user_active_time(request: Request, ndcId: int = 0):
    """
    I dont really wanna trust users and allow minutes farming.
    That's why it's mock

    proof me wrong
    """
    return Base.Answer({})


@mock.post("/g/s/avatar-frame/apply")
@mock.post("/x{ndcId}/s/avatar-frame/apply")
async def avatar_frame_apply_mock(request: Request, ndcId: int = 0):
    return Base.Answer({})


@mock.get("/g/s/topic/0/feed/community")
@mock.get("/g/s/community/trending")
@mock.get("/g/s/community/suggested")
async def recommended_communities_mock(request: Request):
    return Base.Answer({"communityList": [], "paging": {}, "allItemCount": 0})


@mock.get("/g/s/chat/thread/search")
async def useless_chat_search_mock(request: Request):
    return Base.Answer(
        {"threadList": [], "communityInfoMapping": {}, "threadCount": 0, "paging": {}}
    )


@mock.get("/g/s/sticker-collection")
async def stickers_mock(
    request: Request, type: str | None = None, includeStickers: bool = False
):
    if type == "my-active-collection":
        return Base.Answer({"stickerCollectionCount": 0, "stickerCollectionList": []})
    return Base.Answer({"stickerCollectionCount": 0, "stickerCollectionList": []})


@mock.get("/g/s/persona/profile/basic")
async def personabasic_mock(request: Request):
    if not request.state.session["validsession"]:
        return Errors.InvalidSession()

    return Base.Answer(
        {
            "basicProfile": {
                "auid": request.state.session["uid"],
                "age": 20,
                "gender": 1,
                "country_code": "UK",
                "dateOfBirth": 731589,
            }
        }
    )


@mock.get("/g/s/store/sections")
async def storesections_mock(request: Request):
    return Base.Answer({"storeSectionList": []})


@mock.get("/g/s/coupon/new-user-coupon")
async def newusercoupon_mock(request: Request):
    return Base.Answer({"couponMappingList": []})


@mock.get("/g/s/announcement")
async def announcement_mock(request: Request, size: int = 1, language: str = "en"):
    return Base.Answer({"blogList": []})


@mock.get("/g/s/block/full-list")
async def blockedandblocker_mock(request: Request, size: int = 1, language: str = "en"):
    return Base.Answer({"blockedUidList": [], "blockerUidList": []})


@mock.get("/g/s/account/{userId}/mission-set")
async def mission_set_mock(request: Request):
    return Base.Answer(
        {
            "missionSet": {
                "reviewUs": {"completedTime": "2023-09-11T12:37:12Z"},
                "checkInTwoWeeks": {"completedTime": "2023-09-11T12:36:39Z"},
                "invitedOneFriend": {"completedTime": "2023-09-11T12:36:39Z"},
                "followInstagram": {"completedTime": "2023-09-11T12:36:39Z"},
                "downloadAminoMaster": {"completedTime": "2023-09-11T12:36:39Z"},
            }
        }
    )


@mock.get("/g/s/user-profile/{userId}/compose-eligible-check")
async def compose_eligible_check_mock(
    request: Request, objectType: str | None = None, objectSubtype: str | None = None
):
    t1 = timestamp()

    if not isinstance(objectType, str) and not isinstance(objectSubtype, str):
        return Errors.InvalidRequest(timestamp() - t1)

    oT_allowed = ["chat-thread"]
    osT_allowed = ["public"]
    if objectType not in oT_allowed or objectSubtype not in osT_allowed:
        return Errors.InvalidRequest(timestamp() - t1)

    return Base.Answer(spent_time=timestamp() - t1)
