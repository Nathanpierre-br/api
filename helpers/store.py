from datetime import datetime, timezone
from typing import Callable

from objects.types.store import RestrictType, DiscountStatus, StoreItemType


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _restriction(
    price: int = 0,
    restrictType: int | None = None,
    discountStatus: int | None = None,
    discountValue: int | None = None,
    availableDuration: int = 0,
) -> dict:
    return {
        "restrictType": restrictType if restrictType is not None
        else (RestrictType.COIN if price else RestrictType.FREE),
        "restrictValue": price,
        "availableDuration": availableDuration,
        "discountStatus": discountStatus if discountStatus is not None else DiscountStatus.OFF,
        "discountValue": discountValue or 0,
    }


def _timestamps(src: dict) -> tuple[str, str]:
    created = src.get("createdTime") or _iso()
    return created, src.get("modifiedTime") or created



def _ndc_ids(obj: dict, ndcId: int | None = None) -> list:
    availableNdcIds = []
    if isinstance(ndcId, int):
        availableNdcIds = [ndcId]
    return obj.get("availableNdcIds") or availableNdcIds


def _common_ref_fields(obj: dict, restriction: dict, created: str, modified: str, *,
                       ndcId: int | None = None,
                       activated_default: bool = False, new_default: bool = True) -> dict:
    return {
        "md5": obj.get("md5"),
        "status": obj.get("status", 0),
        "version": obj.get("version", 1),
        "createdTime": created,
        "modifiedTime": modified,
        "restrictionInfo": restriction,
        "isActivated": obj.get("isActivated", activated_default),
        "isNew": obj.get("isNew", new_default),
        "ownershipInfo": obj.get("ownershipInfo"),
        "extensions": obj.get("extensions", {}),
        "availableNdcIds": _ndc_ids(obj, ndcId),
    }


# --- refObject builders per type ---

def _build_frame_ref(frame: dict, restriction: dict, created: str, modified: str,
                     ndcId: int | None = None) -> dict:
    return {
        "frameId": frame["frameId"],
        "frameType": frame.get("frameType", 1),
        "name": frame["name"],
        "icon": frame.get("icon"),
        "resourceUrl": frame["resourceUrl"],
        "uid": frame.get("uid"),
        **_common_ref_fields(frame, restriction, created, modified, ndcId=ndcId),
    }


def _build_bubble_ref(bubble: dict, restriction: dict, created: str, modified: str,
                      ndcId: int | None = None) -> dict:
    return {
        "bubbleId": bubble["bubbleId"],
        "bubbleType": bubble.get("bubbleType", 1),
        "name": bubble["name"],
        "resourceUrl": bubble["resourceUrl"],
        "backgroundImage": bubble.get("backgroundImage"),
        "bannerImage": bubble.get("bannerImage"),
        "coverImage": bubble.get("coverImage"),
        "templateId": bubble.get("templateId"),
        "config": bubble.get("config", {}),
        "deletable": bubble.get("ownershipInfo") is not None,
        **_common_ref_fields(bubble, restriction, created, modified, ndcId=ndcId),
    }


def _build_sticker_ref(coll: dict, restriction: dict, created: str, modified: str,
                       ndcId: int | None = None) -> dict:
    return {
        "collectionId": coll["collectionId"],
        "collectionType": coll.get("collectionType", 1),
        "name": coll["name"],
        "icon": coll.get("icon"),
        "smallIcon": coll.get("smallIcon"),
        "bannerUrl": coll.get("bannerUrl"),
        "description": coll.get("description", ""),
        "usedCount": coll.get("usedCount", 0),
        "stickersCount": coll.get("stickersCount", len(coll.get("stickersList", []))),
        "stickersList": coll.get("stickersList", []),
        "uid": coll.get("uid"),
        **_common_ref_fields(coll, restriction, created, modified, ndcId=ndcId),
    }


class StoreItemSpec:
    def __init__(self, *, id_field: str, ref_type: int, icon_field: str,
                 build_ref_object: Callable[..., dict]):
        self.id_field = id_field
        self.ref_type = ref_type
        self.icon_field = icon_field
        self.build_ref_object = build_ref_object


_REF_BUILDERS: dict[int, Callable] = {
    StoreItemType.AvatarFrame: _build_frame_ref,
    StoreItemType.ChatBubble: _build_bubble_ref,
    StoreItemType.StickerCollection: _build_sticker_ref,
}

_ICON_FIELDS: dict[int, str] = {
    StoreItemType.AvatarFrame: "icon",
    StoreItemType.ChatBubble: "coverImage",
    StoreItemType.StickerCollection: "icon",
}

SPECS: dict[str, StoreItemSpec] = {
    group_id: StoreItemSpec(
        id_field=StoreItemType.TYPE_INFO[meta["objectType"]][1],
        ref_type=meta["objectType"],
        icon_field=_ICON_FIELDS[meta["objectType"]],
        build_ref_object=_REF_BUILDERS[meta["objectType"]],
    )
    for group_id, meta in StoreItemType.SECTION_META.items()
}


TYPE_TO_GROUP: dict[int, str] = {
    meta["objectType"]: group_id for group_id, meta in StoreItemType.SECTION_META.items()
}


def build_store_item(spec: StoreItemSpec, obj: dict, price: int | None = None,
                     ndcId: int | None = None, **restr) -> dict:
    price = price or 0
    restriction = _restriction(price=price, availableDuration=obj.get("availableDuration", 0), **restr)
    created, modified = _timestamps(obj)
    return {
        "refObjectId": obj[spec.id_field],
        "refObjectType": spec.ref_type,
        "createdTime": created,
        "itemBasicInfo": {
            "name": obj["name"],
            "icon": obj.get(spec.icon_field),
        },
        "itemRestrictionInfo": restriction,
        "refObject": spec.build_ref_object(obj, restriction, created, modified, ndcId=ndcId),
    }



def build_store_frame_item(frame, price=None, restrictType=None, discountStatus=None, discountValue=None, ndcId=None):
    return build_store_item(SPECS["avatar-frame"], frame, price, ndcId=ndcId,
                            restrictType=restrictType, discountStatus=discountStatus, discountValue=discountValue)


def build_store_bubble_item(bubble, price=None, restrictType=None, discountStatus=None, discountValue=None, ndcId=None):
    return build_store_item(SPECS["chat-bubble"], bubble, price, ndcId=ndcId,
                            restrictType=restrictType, discountStatus=discountStatus, discountValue=discountValue)


def build_store_sticker_item(coll, price=None, restrictType=None, discountStatus=None, discountValue=None, ndcId=None):
    return build_store_item(SPECS["sticker"], coll, price, ndcId=ndcId,
                            restrictType=restrictType, discountStatus=discountStatus, discountValue=discountValue)


def build_store_items_response(items: list, storeSection=None) -> dict:
    return {"storeItemList": items, "storeSection": storeSection}


def build_avatar_frame_response(frame, price=None, restrictType=None, discountStatus=None, discountValue=None, ndcId=None):
    price = price or 0
    restriction = _restriction(price=price, restrictType=restrictType, discountStatus=discountStatus,
                               discountValue=discountValue, availableDuration=frame.get("availableDuration", 0))
    created, modified = _timestamps(frame)
    ref = _build_frame_ref(frame, restriction, created, modified, ndcId=ndcId)
    ref["description"] = frame.get("description", "")
    return {"avatarFrame": ref}


def build_preview_item(group_id: str, doc: dict, ndcId: int | None = None):
    spec = SPECS.get(group_id)
    if spec is None:
        return None
    return build_store_item(
        spec, doc,
        price=doc.get("price", 0),
        ndcId=ndcId,
        restrictType=doc.get("restrictType"),
        discountStatus=doc.get("discountStatus"),
        discountValue=doc.get("discountValue"),
    )


def build_chat_bubble_object(bubble: dict, ndcId: int | None = None) -> dict:
    price = bubble.get("price", 0)
    restriction = _restriction(
        price=price,
        restrictType=bubble.get("restrictType"),
        discountStatus=bubble.get("discountStatus"),
        discountValue=bubble.get("discountValue"),
        availableDuration=bubble.get("availableDuration", 0),
    )
    created, modified = _timestamps(bubble)
    ref = _build_bubble_ref(bubble, restriction, created, modified, ndcId=ndcId)
    ref["isActivated"] = False
    ref["isNew"] = bubble.get("isNew", False)
    return ref

def build_avatar_frame_icon(frame: dict) -> dict | None:
    if not frame:
        return None
    ownership = frame.get("ownershipInfo") or {}
    return {
        "status": frame.get("status", 0),
        "ownershipStatus": ownership.get("ownershipStatus", frame.get("ownershipStatus", 1)),
        "version": frame.get("version", 1),
        "resourceUrl": frame.get("resourceUrl"),
        "name": frame.get("name"),
        "icon": frame.get("icon"),
        "frameType": frame.get("frameType", 1),
        "frameId": frame.get("frameId"),
    }



# --- Ownership ---

async def get_ownership_map(db, uid: str, object_type: int, ids: list[str]) -> dict:
    if not ids:
        return {}
    cursor = db.get(table="UserStoreItems").find(
        {"uid": uid, "objectType": object_type, "objectId": {"$in": ids}},
        {"_id": 0},
    )
    docs = await cursor.to_list(length=None)
    return {d["objectId"]: d for d in docs}


def apply_ownership(doc: dict, id_field: str, own_map: dict) -> dict:
    own = own_map.get(doc.get(id_field))
    if not own:
        return doc
    return {
        **doc,
        "ownershipInfo": own.get("ownershipInfo"),
        "isActivated": own.get("isActivated", False),
        "isNew": False,
    }