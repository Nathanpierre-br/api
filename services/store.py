from datetime import UTC, datetime, timedelta

from helpers.database.mongo import Database
from helpers.store import (
    build_avatar_frame_response,
    build_preview_item,
    build_chat_bubble_object,
    get_ownership_map,
    apply_ownership,
    _iso,
    TYPE_TO_GROUP,
)
from objects.types.store import RestrictType, StoreItemType, PurchaseError


class PurchaseResult:

    __slots__ = ("store_item", "error_code", "error_message")

    def __init__(self, store_item=None, error_code=None, error_message=None):
        self.store_item = store_item
        self.error_code = error_code
        self.error_message = error_message

    @property
    def ok(self) -> bool:
        return self.error_code is None


def _meta(group_id: str) -> dict | None:
    return StoreItemType.SECTION_META.get(group_id)


def _id_field(object_type: int) -> str | None:
    return StoreItemType.TYPE_INFO.get(object_type, (None, None))[1]


class StoreService:

    def __init__(self, db: Database, uid: str, ndcId: int = 0):
        self.db = db
        self.uid = uid
        self.ndcId = ndcId

    @classmethod
    async def create(cls, uid: str, ndcId: int = 0) -> "StoreService":
        db = await Database().init()
        return cls(db, uid, ndcId)

    def close(self):
        self.db.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.close()

    def _collection(self, name: str):
        return self.db.get(table=name)

    async def _owned_map_by_object(self, object_type: int, ids: list[str]) -> dict:
        return await get_ownership_map(self.db, self.uid, object_type, ids)

    def _decorate(self, docs: list[dict], id_field: str | None, own_map: dict) -> list[dict]:
        out = []
        for d in docs:
            if id_field:
                d = apply_ownership(d, id_field, own_map)
            out.append(d)
        return out

    async def _fetch_with_ownership(self, group_id: str, query: dict,
                                    skip: int = 0, limit: int | None = None) -> list[dict]:
        meta = _meta(group_id)
        if not meta:
            return []
        col = self._collection(meta["collection"])
        cursor = col.find(query, {"_id": 0})
        if skip:
            cursor = cursor.skip(skip)
        if limit is not None:
            cursor = cursor.limit(limit)
        docs = await cursor.to_list(length=limit)

        object_type = meta["objectType"]
        id_field = _id_field(object_type)
        own_map = {}
        if id_field:
            ids = [d.get(id_field) for d in docs if d.get(id_field)]
            own_map = await self._owned_map_by_object(object_type, ids)
        return self._decorate(docs, id_field, own_map)

    def _build_items(self, group_id: str, docs: list[dict]) -> list[dict]:
        items = []
        for d in docs:
            item = build_preview_item(group_id, d, ndcId=self.ndcId)
            if item:
                items.append(item)
        return items


    async def list_items(self, group_id: str, start: int = 0, size: int = 25) -> list[dict]:
        docs = await self._fetch_with_ownership(group_id, {}, skip=start, limit=size)
        return self._build_items(group_id, docs)

    async def recommend_items(self, group_id: str, object_id: str | None, size: int = 25) -> list[dict]:
        meta = _meta(group_id)
        if not meta:
            return []
        id_field = _id_field(meta["objectType"])
        query = {id_field: {"$ne": object_id}} if (id_field and object_id) else {}
        docs = await self._fetch_with_ownership(group_id, query, limit=size)
        return self._build_items(group_id, docs)

    async def sections(self, group_ids: list[str]) -> list[dict]:
        section_list = []
        for group_id in group_ids:
            meta = _meta(group_id)
            if not meta:
                continue
            docs = await self._fetch_with_ownership(group_id, {}, limit=6)
            total = await self._collection(meta["collection"]).count_documents({})
            section_list.append({
                "name": meta["name"],
                "sectionGroupId": group_id,
                "storeSectionId": group_id,
                "allItemsCount": total,
                "previewStoreItemList": self._build_items(group_id, docs),
            })
        return section_list


    async def get_avatar_frame(self, frame_id: str) -> dict | None:
        frame = await self._collection("AvatarFrames").find_one({"frameId": frame_id}, {"_id": 0})
        if frame is None:
            return None
        own_map = await self._owned_map_by_object(StoreItemType.AvatarFrame, [frame_id])
        frame = apply_ownership(frame, "frameId", own_map)
        return build_avatar_frame_response(frame, price=frame.get("price", 0), ndcId=self.ndcId)

    async def get_chat_bubble(self, bubble_id: str) -> dict | None:
        bubble = await self._collection("ChatBubbles").find_one({"bubbleId": bubble_id}, {"_id": 0})
        if bubble is None:
            return None
        own_map = await self._owned_map_by_object(StoreItemType.ChatBubble, [bubble_id])
        bubble = apply_ownership(bubble, "bubbleId", own_map)
        return {
            "chatBubble": build_chat_bubble_object(bubble, ndcId=self.ndcId),
            "allChatsBubbleId": bubble.get("bubbleId"),
        }


    async def _owned_docs(self, object_type: int) -> tuple[dict, list[str]]:
        cursor = self._collection("UserStoreItems").find(
            {"uid": self.uid, "objectType": object_type}, {"_id": 0},
        )
        own_docs = await cursor.to_list(length=None)
        own_map = {d["objectId"]: d for d in own_docs}
        return own_map, list(own_map.keys())

    async def list_my_avatar_frames(self, start: int = 0, size: int = 20) -> list[dict]:
        own_map, owned_ids = await self._owned_docs(StoreItemType.AvatarFrame)
        docs = await self._collection("AvatarFrames").find(
            {"frameId": {"$in": owned_ids}}, {"_id": 0},
        ).skip(start).limit(size).to_list(length=size)
        result = []
        for d in docs:
            d = apply_ownership(d, "frameId", own_map)
            result.append(build_avatar_frame_response(d, price=d.get("price", 0), ndcId=self.ndcId)["avatarFrame"])
        return result

    async def list_my_bubbles(self, chat_id: str | None = None,
                              start: int = 0, size: int = 20) -> dict:
        own_map, owned_ids = await self._owned_docs(StoreItemType.ChatBubble)
        docs = await self._collection("ChatBubbles").find(
            {"bubbleId": {"$in": owned_ids}}, {"_id": 0},
        ).skip(start).limit(size).to_list(length=size)

        chat_bubble_list = []
        for d in docs:
            d = apply_ownership(d, "bubbleId", own_map)
            chat_bubble_list.append(build_chat_bubble_object(d, ndcId=self.ndcId))

        user_table = self.db.get(f"x{self.ndcId}", "Users") if self.ndcId else self._collection("Users")
        user = await user_table.find_one({"id": self.uid}) or {}
        default_bubble_id = user.get("bubbleId")
        per_chat = (user.get("chatBubbles") or {}).get(chat_id) if chat_id else None

        return {
            "chatBubbleList": chat_bubble_list,
            "allChatsBubbleId": default_bubble_id,
            "currentSelectedBubbleId": per_chat or default_bubble_id,
        }


    async def purchase(self, object_id: str, object_type: int) -> PurchaseResult:
        if object_type not in StoreItemType.TYPE_INFO:
            return PurchaseResult(error_code="invalid")

        collection, id_field = StoreItemType.TYPE_INFO[object_type]
        item = await self._collection(collection).find_one({id_field: object_id})
        if item is None:
            return PurchaseResult(error_code="invalid")

        owned = self._collection("UserStoreItems")
        existing = await owned.find_one({
            "uid": self.uid, "objectType": object_type, "objectId": object_id,
        })

        group_id = TYPE_TO_GROUP.get(object_type, "avatar-frame")

        if existing:
            store_item = self._finalize_item(item, group_id, existing.get("ownershipInfo"),
                                             existing.get("isActivated", False))
            return PurchaseResult(store_item=store_item)

        restrict_type = item.get("restrictType")
        price = item.get("price", 0)
        if restrict_type is None:
            restrict_type = RestrictType.COIN if price else RestrictType.FREE
        if restrict_type == RestrictType.NONE:
            return PurchaseResult(error_code="invalid")

        if restrict_type == RestrictType.AMINO_MEMBERSHIP:
            u = await self._collection("Users").find_one({"id": self.uid}, {"isPaidSubscriber": 1})
            if not u or not u.get("isPaidSubscriber"):
                return PurchaseResult(error_code=PurchaseError.MEMBERSHIP_NOT_SATISFIED,
                                      error_message="Membership required")

        if restrict_type == RestrictType.COIN and price > 0:
            result = await self._collection("Users").update_one(
                {"id": self.uid, "coins": {"$gte": price}},
                {"$inc": {"coins": -price}},
            )
            if result.modified_count == 0:
                return PurchaseResult(error_code=PurchaseError.NOT_ENOUGH_COINS,
                                      error_message="Not enough coins")

        duration = item.get("availableDuration", 0)
        expired = None
        if duration:
            expired = (datetime.now(UTC) + timedelta(days=duration)).strftime("%Y-%m-%dT%H:%M:%SZ")

        ownership_info = {
            "createdTime": _iso(),
            "expiredTime": expired,
            "isAutoRenew": False,
            "ownershipStatus": 1,
        }
        await owned.insert_one({
            "uid": self.uid,
            "objectId": object_id,
            "objectType": object_type,
            "isActivated": False,
            "ownershipInfo": ownership_info,
            "createdTime": _iso(),
        })

        store_item = self._finalize_item(item, group_id, ownership_info, False)
        return PurchaseResult(store_item=store_item)

    def _finalize_item(self, item: dict, group_id: str,
                       ownership_info, is_activated: bool) -> dict:
        item = {**item}
        item.pop("_id", None)
        item["ownershipInfo"] = ownership_info
        item["isActivated"] = is_activated
        item["isNew"] = False
        return build_preview_item(group_id, item, ndcId=self.ndcId)