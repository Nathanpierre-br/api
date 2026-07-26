from datetime import datetime, timezone

from objects.types.store import RestrictType, DiscountStatus


def _iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _restriction(
    price: int = 0,
    restrictType: int | None = None,
    discountStatus: int | None = None,
    discountValue: int | None = None,
    availableDuration: int = 0,
) -> dict:
    if restrictType is None:
        restrictType = RestrictType.COIN if price else RestrictType.FREE
    if discountStatus is None:
        discountStatus = DiscountStatus.OFF
    if discountValue is None:
        discountValue = 0

    return {
        "restrictType": restrictType,
        "restrictValue": price,
        "availableDuration": availableDuration,
        "discountStatus": discountStatus,
        "discountValue": discountValue,
    }


def build_store_frame_item(
    frame: dict,
    price: int | None = None,
    restrictType: int | None = None,
    discountStatus: int | None = None,
    discountValue: int | None = None,
) -> dict:
    if price is None:
        price = 0

    restriction = _restriction(
        price=price,
        restrictType=restrictType,
        discountStatus=discountStatus,
        discountValue=discountValue,
        availableDuration=frame.get("availableDuration", 0),
    )

    created = frame.get("createdTime") or _iso()
    modified = frame.get("modifiedTime") or created

    return {
        "refObjectId": frame["frameId"],
        "refObjectType": 122,
        "createdTime": created,
        "itemBasicInfo": {
            "name": frame["name"],
            "icon": frame.get("icon"),
        },
        "itemRestrictionInfo": restriction,
        "refObject": {
            "frameId": frame["frameId"],
            "frameType": frame.get("frameType", 1),
            "name": frame["name"],
            "icon": frame.get("icon"),
            "resourceUrl": frame["resourceUrl"],
            "md5": frame.get("md5"),
            "status": frame.get("status", 0),
            "version": frame.get("version", 1),
            "uid": frame.get("uid"),
            "createdTime": created,
            "modifiedTime": modified,
            "restrictionInfo": restriction,
            "isActivated": frame.get("isActivated", False),
            "isNew": frame.get("isNew", True),
            "ownershipInfo": frame.get("ownershipInfo"),
            "extensions": frame.get("extensions", {}),
            "availableNdcIds": frame.get("availableNdcIds", [])
        },
    }


def build_store_bubble_item(
    bubble: dict,
    price: int | None = None,
    restrictType: int | None = None,
    discountStatus: int | None = None,
    discountValue: int | None = None,
) -> dict:
    if price is None:
        price = 0

    restriction = _restriction(
        price=price,
        restrictType=restrictType,
        discountStatus=discountStatus,
        discountValue=discountValue,
        availableDuration=bubble.get("availableDuration", 0),
    )

    created = bubble.get("createdTime") or _iso()
    modified = bubble.get("modifiedTime") or created

    return {
        "refObjectId": bubble["bubbleId"],
        "refObjectType": 116,
        "createdTime": created,
        "itemBasicInfo": {
            "name": bubble["name"],
            "icon": bubble.get("coverImage"),
        },
        "itemRestrictionInfo": restriction,
        "refObject": {
            "bubbleId": bubble["bubbleId"],
            "bubbleType": bubble.get("bubbleType", 1),
            "name": bubble["name"],
            "resourceUrl": bubble["resourceUrl"],
            "backgroundImage": bubble.get("backgroundImage"),
            "bannerImage": bubble.get("bannerImage"),
            "coverImage": bubble.get("coverImage"),
            "md5": bubble.get("md5"),
            "status": bubble.get("status", 0),
            "version": bubble.get("version", 1),
            "templateId": bubble.get("templateId"),
            "config": bubble.get("config", {}),
            "createdTime": created,
            "modifiedTime": modified,
            "deletable": bubble.get("deletable", True),
            "restrictionInfo": restriction,
            "isActivated": bubble.get("isActivated", False),
            "isNew": bubble.get("isNew", True),
            "ownershipInfo": bubble.get("ownershipInfo"),
            "extensions": bubble.get("extensions", {}),
            "availableNdcIds": bubble.get("availableNdcIds", [])
        },
    }


def build_store_items_response(items: list, storeSection = None) -> dict:
    return {
        "storeItemList": items,
        "storeSection": storeSection,
    }


def build_avatar_frame_response(
    frame: dict,
    price: int | None = None,
    restrictType: int | None = None,
    discountStatus: int | None = None,
    discountValue: int | None = None,
) -> dict:
    """Ответ /avatar-frame/{frameId}."""
    if price is None:
        price = 0

    restriction = _restriction(
        price=price,
        restrictType=restrictType,
        discountStatus=discountStatus,
        discountValue=discountValue,
        availableDuration=frame.get("availableDuration", 0),
    )

    created = frame.get("createdTime") or _iso()
    modified = frame.get("modifiedTime") or created

    return {
        "avatarFrame": {
            "frameId": frame["frameId"],
            "frameType": frame.get("frameType", 1),
            "name": frame["name"],
            "icon": frame.get("icon"),
            "resourceUrl": frame["resourceUrl"],
            "md5": frame.get("md5"),
            "status": frame.get("status", 0),
            "version": frame.get("version", 1),
            "uid": frame.get("uid"),
            "createdTime": created,
            "modifiedTime": modified,
            "description": frame.get("description", ""),
            "restrictionInfo": restriction,
            "isActivated": frame.get("isActivated", False),
            "isNew": frame.get("isNew", True),
            "ownershipInfo": frame.get("ownershipInfo"),
            "extensions": frame.get("extensions", {}),
            "availableNdcIds": frame.get("availableNdcIds", [])
        }
    }


def build_preview_item(group_id: str, doc: dict):
    price = doc.get("price", 0)
    if group_id == "avatar-frame":
        return build_store_frame_item(doc, price=price)
    if group_id == "chat-bubble":
        return build_store_bubble_item(doc, price=price)
    return None




def build_chat_bubble_object(bubble: dict) -> dict:
    price = bubble.get("price", 0)
    restriction = _restriction(
        price=price,
        restrictType=bubble.get("restrictType"),
        discountStatus=bubble.get("discountStatus"),
        discountValue=bubble.get("discountValue"),
        availableDuration=bubble.get("availableDuration", 0),
    )
    created = bubble.get("createdTime") or _iso()
    return {
        "bubbleId": bubble["bubbleId"],
        "bubbleType": bubble.get("bubbleType", 1),
        "name": bubble["name"],
        "resourceUrl": bubble["resourceUrl"],
        "backgroundImage": bubble.get("backgroundImage"),
        "bannerImage": bubble.get("bannerImage"),
        "coverImage": bubble.get("coverImage"),
        "md5": bubble.get("md5"),
        "status": bubble.get("status", 0),
        "version": bubble.get("version", 1),
        "templateId": bubble.get("templateId"),
        "config": bubble.get("config", {}),
        "createdTime": created,
        "modifiedTime": bubble.get("modifiedTime") or created,
        "deletable": bubble.get("deletable", True),
        "restrictionInfo": restriction,
        "isActivated": True,
        "isNew": bubble.get("isNew", False),
        "ownershipInfo": bubble.get("ownershipInfo"),
        "extensions": bubble.get("extensions", {}),
        "availableNdcIds": bubble.get("availableNdcIds", [])
    }