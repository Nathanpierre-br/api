

class StoreItemType:
    StickerCollection: int = 114
    ChatBubble: int = 116
    AvatarFrame: int = 122

    STORE_SECTIONS = (StickerCollection, ChatBubble, AvatarFrame)


class RestrictType:
    NONE = 0
    FREE = 1
    AMINO_MEMBERSHIP = 2
    NO_RESTRICTION = 3
    COIN = 4


class DiscountStatus:
    OFF = 0
    AMINO_PLUS = 1

class PurchaseError:
    NOT_ENOUGH_COINS = 4300
    MEMBERSHIP_NOT_SATISFIED = 4101
    COMMUNITY_NOT_SATISFIED = 4102