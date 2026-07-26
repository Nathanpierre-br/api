from datetime import UTC, datetime, timedelta
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
    build_preview_item,
    build_chat_bubble_object,
)
from objects import Base, Errors
from objects.types.store import (
    RestrictType, StoreItemType, PurchaseError,
)

store = APIRouter()
store.route_class = CachableRoute


def _iso():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _get_ownership_map(db, uid: str, object_type: int, ids: list[str]) -> dict:
    if not ids:
        return {}
    owned = db.get(table="UserStoreItems")
    cursor = owned.find(
        {"uid": uid, "objectType": object_type, "objectId": {"$in": ids}},
        {"_id": 0},
    )
    docs = await cursor.to_list(length=None)
    return {d["objectId"]: d for d in docs}


def _apply_ownership(doc: dict, id_field: str, own_map: dict) -> dict:
    own = own_map.get(doc.get(id_field))
    if own:
        doc = {**doc}
        doc["ownershipInfo"] = own.get("ownershipInfo")
        doc["isActivated"] = own.get("isActivated", False)
        doc["isNew"] = False
    return doc




@store.get("/x{ndcId}/s/store/items")
@store.get("/g/s/store/items")
@validauth_required
async def get_store_items(request: Request, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]

    group_id = request.query_params.get("sectionGroupId", "avatar-frame")
    start = int(request.query_params.get("start", 0))
    size = int(request.query_params.get("size", 25))

    meta = StoreItemType.SECTION_META.get(group_id)
    if not meta:
        return Base.Answer(build_store_items_response([]), spent_time=timestamp() - t1)

    db = await Database().init()
    try:
        col = db.get(table=meta["collection"])
        docs = await col.find({}).skip(start).limit(size).to_list(length=size)

        object_type = meta["objectType"]
        id_field = StoreItemType.TYPE_INFO.get(object_type, (None, None))[1]

        own_map = {}
        if id_field:
            ids = [d.get(id_field) for d in docs if d.get(id_field)]
            own_map = await _get_ownership_map(db, uid, object_type, ids)

        items = []
        for d in docs:
            if id_field:
                d = _apply_ownership(d, id_field, own_map)
            item = build_preview_item(group_id, d)
            if item:
                items.append(item)
    finally:
        db.close()

    return Base.Answer(build_store_items_response(items), spent_time=timestamp() - t1)



@store.get("/x{ndcId}/s/avatar-frame/{frameId}")
@store.get("/g/s/avatar-frame/{frameId}")
@validauth_required
async def get_avatar_frame(request: Request, frameId: str, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]

    db = await Database().init()
    try:
        frames = db.get(table="AvatarFrames")
        frame = await frames.find_one({"frameId": frameId}, {"_id": 0})
        if frame is None:
            return Errors.InvalidRequest(timestamp() - t1)

        own_map = await _get_ownership_map(
            db, uid, StoreItemType.AvatarFrame, [frameId]
        )
        frame = _apply_ownership(frame, "frameId", own_map)
    finally:
        db.close()

    return Base.Answer(
        build_avatar_frame_response(frame, price=frame.get("price", 0)),
        spent_time=timestamp() - t1,
    )


def _group_for_type(object_type: int) -> str:
    for gid, meta in StoreItemType.SECTION_META.items():
        if meta["objectType"] == object_type:
            return gid
    return "avatar-frame"
  



@store.post("/x{ndcId}/s/store/purchase")
@store.post("/g/s/store/purchase")
@validauth_required
async def store_purchase(request: Request, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]

    try:
        data = await request.json()
        object_id = data["objectId"]
        object_type = int(data["objectType"])
    except Exception:
        return Errors.InvalidRequest(timestamp() - t1)

    if object_type not in StoreItemType.TYPE_INFO:
        return Errors.InvalidRequest(timestamp() - t1)

    collection, id_field = StoreItemType.TYPE_INFO[object_type]

    db = await Database().init()
    try:
        col = db.get(table=collection)
        item = await col.find_one({id_field: object_id})
        if item is None:
            return Errors.InvalidRequest(timestamp() - t1)

        owned = db.get(table="UserStoreItems")
        existing = await owned.find_one({
            "uid": uid,
            "objectType": object_type,
            "objectId": object_id,
        })

        if existing:
            item.pop("_id", None)
            item["ownershipInfo"] = existing.get("ownershipInfo")
            item["isActivated"] = existing.get("isActivated", False)
            item["isNew"] = False
            store_item = build_preview_item(_group_for_type(object_type), item)
            return Base.Answer({"storeItem": store_item}, spent_time=timestamp() - t1)

        restrict_type = item.get("restrictType")
        price = item.get("price", 0)
        if restrict_type is None:
            restrict_type = RestrictType.COIN if price else RestrictType.FREE

        if restrict_type == RestrictType.NONE:
            return Errors.InvalidRequest(timestamp() - t1)

        if restrict_type == RestrictType.AMINO_MEMBERSHIP:
            users = db.get(table="Users")
            u = await users.find_one({"id": uid}, {"isPaidSubscriber": 1})
            if not u or not u.get("isPaidSubscriber"):
                return Errors.Custom(
                    PurchaseError.MEMBERSHIP_NOT_SATISFIED,
                    "Membership required",
                    spent_time=timestamp() - t1,
                )

        if restrict_type == RestrictType.COIN and price > 0:
            users = db.get(table="Users")
            result = await users.update_one(
                {"id": uid, "coins": {"$gte": price}},
                {"$inc": {"coins": -price}},
            )
            if result.modified_count == 0:
                return Errors.Custom(
                    PurchaseError.NOT_ENOUGH_COINS,
                    "Not enough coins",
                    spent_time=timestamp() - t1,
                )

        duration = item.get("availableDuration", 0)
        expired = None
        if duration:
            expired = (datetime.now(UTC) + timedelta(days=duration)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

        ownership_info = {
            "createdTime": _iso(),
            "expiredTime": expired,
            "isAutoRenew": False,
            "ownershipStatus": 1,
        }
        ownership = {
            "uid": uid,
            "objectId": object_id,
            "objectType": object_type,
            "isActivated": False,
            "ownershipInfo": ownership_info,
            "createdTime": _iso(),
        }
        await owned.insert_one(ownership)

        item.pop("_id", None)
        item["ownershipInfo"] = ownership_info
        item["isActivated"] = False
        item["isNew"] = False
        store_item = build_preview_item(_group_for_type(object_type), item)

    finally:
        db.close()

    return Base.Answer({"storeItem": store_item}, spent_time=timestamp() - t1)





@store.get("/g/s/store/sections")
@store.get("/x{ndcId}/s/store/sections")
@validauth_required
async def storesections(request: Request, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]

    raw = request.query_params.get("storeSectionGroupIds", "")
    wanted = [x.strip() for x in raw.split(",") if x.strip()] or list(StoreItemType.SECTION_META)

    db = await Database().init()
    try:
        section_list = []
        for group_id in wanted:
            meta = StoreItemType.SECTION_META.get(group_id)
            if not meta:
                continue

            col = db.get(table=meta["collection"])
            docs = await col.find({}).to_list(length=6)
            total = await col.count_documents({})

            object_type = meta["objectType"]
            id_field = StoreItemType.TYPE_INFO.get(object_type, (None, None))[1]

            own_map = {}
            if id_field:
                ids = [d.get(id_field) for d in docs if d.get(id_field)]
                own_map = await _get_ownership_map(db, uid, object_type, ids)

            preview = []
            for d in docs:
                if id_field:
                    d = _apply_ownership(d, id_field, own_map)
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
    finally:
        db.close()

    return Base.Answer({"storeSectionList": section_list}, spent_time=timestamp() - t1)



@store.get("/x{ndcId}/s/chat/chat-bubble/{bubbleId}")
@store.get("/g/s/chat/chat-bubble/{bubbleId}")
@validauth_required
async def get_chat_bubble(request: Request, bubbleId: str, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]

    db = await Database().init()
    try:
        bubbles = db.get(table="ChatBubbles")
        bubble = await bubbles.find_one({"bubbleId": bubbleId}, {"_id": 0})
        if bubble is None:
            return Errors.InvalidRequest(timestamp() - t1)

        own_map = await _get_ownership_map(db, uid, StoreItemType.ChatBubble, [bubbleId])
        bubble = _apply_ownership(bubble, "bubbleId", own_map)
    finally:
        db.close()

    return Base.Answer(
        {
            "chatBubble": build_chat_bubble_object(bubble),
            "allChatsBubbleId": bubble.get("bubbleId"),
        },
        spent_time=timestamp() - t1,
    )






@store.get("/x{ndcId}/s/store/recommend-items")
@store.get("/g/s/store/recommend-items")
@validauth_required
async def recommend_items(request: Request, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]

    group_id = request.query_params.get("sectionGroupId", "avatar-frame")
    object_id = request.query_params.get("objectId")
    size = int(request.query_params.get("size", 25))

    meta = StoreItemType.SECTION_META.get(group_id)
    if not meta:
        return Base.Answer(build_store_items_response([]), spent_time=timestamp() - t1)

    db = await Database().init()
    try:
        col = db.get(table=meta["collection"])
        id_field = StoreItemType.TYPE_INFO.get(meta["objectType"], (None, None))[1]

        query = {id_field: {"$ne": object_id}} if (id_field and object_id) else {}
        docs = await col.find(query).limit(size).to_list(length=size)

        object_type = meta["objectType"]
        own_map = {}
        if id_field:
            ids = [d.get(id_field) for d in docs if d.get(id_field)]
            own_map = await _get_ownership_map(db, uid, object_type, ids)

        items = []
        for d in docs:
            if id_field:
                d = _apply_ownership(d, id_field, own_map)
            item = build_preview_item(group_id, d)
            if item:
                items.append(item)
    finally:
        db.close()

    return Base.Answer(build_store_items_response(items), spent_time=timestamp() - t1)



@store.get("/x{ndcId}/s/avatar-frame")
@store.get("/g/s/avatar-frame")
@validauth_required
async def list_my_avatar_frames(request: Request, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]

    start = int(request.query_params.get("start", 0))
    size = int(request.query_params.get("size", 20))

    db = await Database().init()
    try:
        owned = db.get(table="UserStoreItems")
        own_docs = await owned.find(
            {"uid": uid, "objectType": StoreItemType.AvatarFrame},
            {"_id": 0},
        ).to_list(length=None)

        own_map = {d["objectId"]: d for d in own_docs}
        owned_ids = list(own_map.keys())

        frames = db.get(table="AvatarFrames")
        docs = await frames.find(
            {"frameId": {"$in": owned_ids}}, {"_id": 0}
        ).skip(start).limit(size).to_list(length=size)

        result = []
        for d in docs:
            d = _apply_ownership(d, "frameId", own_map)
            result.append(build_avatar_frame_response(d, price=d.get("price", 0))["avatarFrame"])
    finally:
        db.close()

    return Base.Answer({"avatarFrameList": result}, spent_time=timestamp() - t1)



@store.get("/x{ndcId}/s/chat/chat-bubble")
@store.get("/g/s/chat/chat-bubble")
@validauth_required
async def list_my_bubbles(request: Request, ndcId: int = 0):
    t1 = timestamp()
    uid = request.state.session["uid"]

    bubble_type = request.query_params.get("type", "all-my-bubbles")
    start = int(request.query_params.get("start", 0))
    size = int(request.query_params.get("size", 20))

    db = await Database().init()
    try:
        owned = db.get(table="UserStoreItems")
        own_docs = await owned.find(
            {"uid": uid, "objectType": StoreItemType.ChatBubble},
            {"_id": 0},
        ).to_list(length=None)

        own_map = {d["objectId"]: d for d in own_docs}
        owned_ids = list(own_map.keys())

        bubbles = db.get(table="ChatBubbles")
        docs = await bubbles.find(
            {"bubbleId": {"$in": owned_ids}}, {"_id": 0}
        ).skip(start).limit(size).to_list(length=size)

        chat_bubble_list = []
        for d in docs:
            d = _apply_ownership(d, "bubbleId", own_map)
            chat_bubble_list.append(build_chat_bubble_object(d))
    finally:
        db.close()

    return Base.Answer(
        {
            "chatBubbleList": chat_bubble_list,
            "allChatsBubbleId": None,
            "currentSelectedBubbleId": None,
        },
        spent_time=timestamp() - t1,
    )








@store.get("/g/s/store/subscription")
@validauth_required
async def get_store_subscription(request: Request):
    t1 = timestamp()
    return Base.Answer({"storeSubscriptionItemList": []}, spent_time=timestamp() - t1)


@store.get("/x{ndcId}/s/store/recommend-store-by-product")
@store.get("/g/s/store/recommend-store-by-product")
@validauth_required
async def recommend_store_by_product(request: Request, ndcId: int = 0):
    t1 = timestamp()
    return Base.Answer(
        {"communityList": [], "storeItemCommunityCheckList": []},
        spent_time=timestamp() - t1,
    )