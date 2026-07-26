from datetime import UTC, datetime
from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.config import Config
from helpers.database.mongo import Database
from helpers.decorators.validauth import validauth_required
from helpers.routers.cachable import CachableRoute
from helpers.store import (
    build_avatar_frame_response,
    build_store_bubble_item,
    build_store_frame_item,
    build_store_items_response,
    build_preview_item
)
from objects import Base, Errors
from objects.types.store import RestrictType, DiscountStatus

store = APIRouter()
store.route_class = CachableRoute



from datetime import UTC, datetime
from time import time as timestamp

from fastapi import APIRouter, Request

from helpers.config import Config
from helpers.database.mongo import Database
from helpers.decorators.validauth import validauth_required
from helpers.routers.cachable import CachableRoute
from helpers.store import (
    build_avatar_frame_response,
    build_store_bubble_item,
    build_store_frame_item,
    build_store_items_response,
)
from objects import Base, Errors
from objects.types.store import RestrictType, DiscountStatus, StoreItemType

store = APIRouter()
store.route_class = CachableRoute


@store.get("/x{ndcId}/s/store/items")
@store.get("/g/s/store/items")
@validauth_required
async def get_store_items(request: Request, ndcId: int = 0):
    t1 = timestamp()

    group_id = request.query_params.get("sectionGroupId", "avatar-frame")
    start = int(request.query_params.get("start", 0))
    size = int(request.query_params.get("size", 25))

    meta = StoreItemType.SECTION_META.get(group_id)
    if not meta:
        return Base.Answer(build_store_items_response([]), spent_time=timestamp() - t1)

    connection = await Database().init()
    col = connection.get(f"x{ndcId}", meta["collection"])
    docs = await col.find({}).skip(start).limit(size).to_list(length=size)
    connection.close()

    items = []
    for d in docs:
        item = build_preview_item(group_id, d)
        if item:
            items.append(item)

    return Base.Answer(
        build_store_items_response(items),
        spent_time=timestamp() - t1,
    )


@store.get("/x{ndcId}/s/avatar-frame/{frameId}")
@store.get("/g/s/avatar-frame/{frameId}")
@validauth_required
async def get_avatar_frame(request: Request, frameId: str, ndcId: int = 0):
    t1 = timestamp()

    connection = await Database().init()
    frames = connection.get(f"x{ndcId}", "AvatarFrames")
    frame = await frames.find_one({"frameId": frameId})
    connection.close()

    if frame is None:
        return Errors.InvalidRequest(timestamp() - t1)

    return Base.Answer(
        build_avatar_frame_response(frame, frame, price=frame.get("price", 0)),
        spent_time=timestamp() - t1
    )



@store.post("/x{ndcId}/s/store/purchase")
@store.post("/g/s/store/purchase")
@validauth_required
async def store_purchase(request: Request, ndcId: int = 0):
    t1 = timestamp()
    data = await request.json()

    object_id = data.get("objectId")
    object_type = data.get("objectType")
    payment_context = data.get("paymentContext", {})

    if not object_id or object_type not in StoreItemType.STORE_SECTIONS:
        return Errors.InvalidRequest(timestamp() - t1)

    uid = request.state.session["uid"]

    # TODO: 1) достать товар и цену из БД (цену НЕ брать из запроса!)
    # TODO: 2) проверить restrictType (2=membership, 4=coin)
    # TODO: 3) атомарно списать монеты, при нехватке -> 4300
    # TODO: 4) записать ownership юзеру
    # заглушка: считаем успешной
    return Base.Answer(spent_time=timestamp() - t1)



@store.get("/g/s/store/subscription")
@validauth_required
async def get_store_subscription(request: Request):
    t1 = timestamp()
    # TODO: список подписок пользователя

    return Base.Answer(
        {
            "storeSubscriptionItemList": []
        },
        spent_time=timestamp() - t1
    )

@store.get("/x{ndcId}/s/store/recommend-store-by-product")
@store.get("/g/s/store/recommend-store-by-product")
@validauth_required
async def recommend_store_by_product(request: Request, ndcId: int = 0):
    t1 = timestamp()
    # объект, по которому рекомендуют (objectId=frameId, objectType=122)
    # object_id = request.query_params.get("objectId")
    # object_type = request.query_params.get("objectType")

    # TODO: список сообществ, где доступен товар
    return Base.Answer(
        {
            "communityList": [],
            "storeItemCommunityCheckList": []
        },
        spent_time=timestamp() - t1
    )


@store.get("/g/s/store/sections")
@store.get("/x{ndcId}/s/store/sections")
@validauth_required
async def storesections(request: Request, ndcId: int = 0):
    t1 = timestamp()

    raw = request.query_params.get("storeSectionGroupIds", "")
    wanted = [x.strip() for x in raw.split(",") if x.strip()] or list(StoreItemType.SECTION_META)

    connection = await Database().init()
    section_list = []

    for group_id in wanted:
        meta = StoreItemType.SECTION_META.get(group_id)
        if not meta:
            continue

        col = connection.get(f"x{ndcId}", meta["collection"])
        docs = await col.find({}).to_list(length=6)
        total = await col.count_documents({})

        preview = []
        for d in docs:
            item = build_preview_item(group_id, d)
            if item:
                preview.append(item)

        section_list.append({
            "name": meta["name"],
            "sectionGroupId": group_id,
            "storeSectionId": group_id,
            "allItemsCount": total,
            "previewStoreItemList": preview,
        })

    connection.close()

    return Base.Answer(
        {"storeSectionList": section_list},
        spent_time=timestamp() - t1,
    )