from hashlib import sha256
from typing import Union

from helpers.database.mongo import Database

from .medialist import MediaList
from .user import User

"""
this is top tier bullshit
"""


RANKING_TABLE = [
    {"id": "1", "level": 1, "reputation": 0, "title": "Level 1"},
    {"id": "2", "level": 2, "reputation": 20, "title": "Level 2"},
    {"id": "3", "level": 3, "reputation": 70, "title": "Level 3"},
    {"id": "4", "level": 4, "reputation": 170, "title": "Level 4"},
    {"id": "5", "level": 5, "reputation": 320, "title": "Level 5"},
    {"id": "6", "level": 6, "reputation": 535, "title": "Level 6"},
    {"id": "7", "level": 7, "reputation": 835, "title": "Level 7"},
    {"id": "8", "level": 8, "reputation": 1235, "title": "Level 8"},
    {"id": "9", "level": 9, "reputation": 1750, "title": "Level 9"},
    {"id": "10", "level": 10, "reputation": 2400, "title": "Level 10"},
    {"id": "11", "level": 11, "reputation": 3200, "title": "Level 11"},
    {"id": "12", "level": 12, "reputation": 4200, "title": "Level 12"},
    {"id": "13", "level": 13, "reputation": 5400, "title": "Level 13"},
    {"id": "14", "level": 14, "reputation": 6800, "title": "Level 14"},
    {"id": "15", "level": 15, "reputation": 8500, "title": "Level 15"},
    {"id": "16", "level": 16, "reputation": 10500, "title": "Level 16"},
    {"id": "17", "level": 17, "reputation": 12800, "title": "Level 17"},
    {"id": "18", "level": 18, "reputation": 15500, "title": "Level 18"},
    {"id": "19", "level": 19, "reputation": 18700, "title": "Level 19"},
    {"id": "20", "level": 20, "reputation": 22500, "title": "Level 20"},
]


MODULE_DEFAULTS = {
    "post": True,
    "chat": True,
    "ranking": True,
    "leaderboard": False,
    "featured": False,
    "catalog": False,
    "sharedFolder": False,
    "influencer": False,
    "topicCategories": False,
    "externalContent": False,
}


def _mod_enabled(mods: dict, name: str) -> bool:
    m = mods.get(name)
    if isinstance(m, dict):
        return bool(m.get("enabled", MODULE_DEFAULTS.get(name, True)))
    if isinstance(m, bool):
        return m
    return MODULE_DEFAULTS.get(name, True)


_DEFAULT_PAGES = [
    (
        {
            "url": "ndc://leaderboards",
            "alias": None,
            "id": "leaderboards-default",
            "parentId": None,
            "originalTitle": None,
        },
        "ranking",
    ),
    (
        {
            "url": "ndc://featured",
            "alias": None,
            "id": "featured-default",
            "parentId": None,
            "originalTitle": None,
        },
        "featured",
    ),
    (
        {
            "url": "ndc://my-chats",
            "alias": None,
            "id": "chat-default",
            "parentId": None,
            "originalTitle": None,
        },
        "chat",
    ),
    (
        {
            "url": "ndc://public-chats",
            "alias": None,
            "id": "chat-public-chats",
            "parentId": None,
            "originalTitle": None,
        },
        "chat",
    ),
    (
        {
            "url": "ndc://latest-posts",
            "alias": None,
            "id": "post-latest-feed",
            "parentId": None,
            "originalTitle": None,
        },
        "post",
    ),
    (
        {
            "url": "ndc://following-feed",
            "alias": None,
            "id": "post-following-feed",
            "parentId": None,
            "originalTitle": None,
        },
        "post",
    ),
    (
        {
            "url": "ndc://image-posts",
            "alias": None,
            "id": "post-image-posts",
            "parentId": None,
            "originalTitle": None,
        },
        "post",
    ),
    (
        {
            "url": "ndc://blogs",
            "alias": None,
            "id": "post-blogs",
            "parentId": None,
            "originalTitle": None,
        },
        "post",
    ),
    (
        {
            "url": "ndc://questions",
            "alias": None,
            "id": "post-questions",
            "parentId": None,
            "originalTitle": None,
        },
        "post",
    ),
    (
        {
            "url": "ndc://polls",
            "alias": None,
            "id": "post-polls",
            "parentId": None,
            "originalTitle": None,
        },
        "post",
    ),
    (
        {
            "url": "ndc://catalog",
            "alias": None,
            "id": "catalog-default",
            "parentId": None,
            "originalTitle": None,
        },
        "catalog",
    ),
    (
        {
            "url": "ndc://shared-folder",
            "alias": None,
            "id": "shared-folder",
            "parentId": None,
            "originalTitle": None,
        },
        "sharedFolder",
    ),
    (
        {
            "url": "ndc://blog-categories",
            "alias": None,
            "id": "topic-categories-default",
            "parentId": None,
            "originalTitle": None,
        },
        "topicCategories",
    ),
    (
        {
            "url": "ndc://guidelines",
            "alias": None,
            "id": "guidelines",
            "parentId": None,
            "originalTitle": None,
        },
        None,
    ),
]


def _build_pages(mods: dict, conf: dict) -> dict:
    default_list = [
        page
        for page, gate in _DEFAULT_PAGES
        if gate is None or _mod_enabled(mods, gate)
    ]
    return {
        "defaultList": conf.get("pageDefaultList", default_list),
        "customList": conf.get("pageCustomList", []),
    }


def _build_appearance(conf: dict) -> dict:
    return {
        "leftSidePanel": {
            "style": {
                "iconColor": conf.get("sidepanelIconColor"),
            },
            "navigation": {
                "level1": conf.get(
                    "sidepanelTopNav",
                    [
                        {"id": "guidelines"},
                        {"id": "chat-default"},
                        {"id": "chat-public-chats"},
                    ],
                ),
                "level2": conf.get("sidepanelBottomNav", []),
            },
        },
        "homePage": {
            "navigation": conf.get(
                "homepageNav",
                [
                    {"id": "guidelines"},
                    {"id": "post-latest-feed", "isStartPage": True},
                    {"id": "chat-public-chats"},
                ],
            ),
        },
    }


def _mod_field(mods: dict, name: str, field: str, default):
    m = mods.get(name)
    if isinstance(m, dict):
        return m.get(field, default)
    return default


class Communities:
    @staticmethod
    def ModuleInfo(module_data: dict):
        return {
            "enabled": module_data.get("enabled", True),
            "privilege": {
                "type": module_data.get("accessType", 1),
                "minLevel": module_data.get("minLevel", 3),
            },
        }

    @staticmethod
    async def Info(
        ndcId: int | dict,
        connection=None,
        trigger_uid: Union[str, None] = None,
    ):
        if not connection:
            connection = await Database().init()
        if isinstance(ndcId, int) or isinstance(ndcId, str):
            comms = connection.get(table="Communities")
            data = await comms.find_one({"id": ndcId})
        else:
            data = ndcId
            ndcId = data["id"]

        table = connection.get(f"x{ndcId}", "Users")
        host_xndcId = await table.find_one({"id": data["agent"]})
        agent = User.OwnNonSensetiveProfile(host_xndcId, ndcId) if host_xndcId else None

        membershipStatus = 0
        if trigger_uid and (
            trigger_uid == data.get("agent")
            or trigger_uid in data.get("memberList", [])
        ):
            membershipStatus = 1

        conf = data.get("configuration", {})
        mods = conf.get("modules", {})
        adv = conf.get("advancedSettings", {})

        chat_mod = mods.get("chat", {})
        blog_mod = mods.get("blog", {})
        poll_mod = mods.get("poll", {})
        image_mod = mods.get("image", {})
        question_mod = mods.get("question", {})

        av = chat_mod.get("avChat", {}) if isinstance(chat_mod, dict) else {}

        return {
            "agent": agent,
            "ndcId": ndcId,
            "name": data["name"],
            "link": "http://altamino.top/c/" + data["aminoId"],
            "endpoint": data["aminoId"],
            "membershipStatus": membershipStatus,
            "icon": data["icon"],
            "status": data["status"],
            "membersCount": data.get("membersCount", 0),
            "joinType": data.get("joinType", 0),
            "content": data.get("description", ""),
            "tagline": data.get("tagline", ""),
            "templateId": data.get("templateId", 9),
            "communityHeat": data.get("heat", 0.00),
            "extensions": {},
            "createdTime": data.get("createdTime", "2023-01-01T12:00:00Z"),
            "modifiedTime": data.get("modifiedTime", "2023-01-01T12:00:00Z"),
            "userAddedTopicList": data.get("userAddedTopicList", []),
            "searchable": data.get("searchable", True),
            "influencerList": data.get("influencerList", []),
            "primaryLanguage": data.get("lang", "en"),
            "isStandaloneAppDeprecated": False,
            "listedStatus": data.get("listedStatus", 2),
            "probationStatus": data.get("probationStatus", 0),
            "hidden": data.get("hidden", False),
            "themePack": {
                "themeColor": data.get("themeColor", "#1B1C43"),
                "themePackUrl": data.get("themeUrl"),
                "themePackHash": data.get(
                    "themeHash",
                    sha256(
                        data.get("themeUrl", "https://trolo.lol/example").encode(
                            "utf-8"
                        )
                    ).hexdigest(),
                ),
                "themePackRevision": data.get("themeRevision"),
            },
            "mediaList": data.get("mediaList", []),
            "isStandaloneAppMonetizationEnabled": False,
            "activeInfo": {},
            "configuration": {
                "page": _build_pages(mods, conf),
                "module": {
                    "post": {
                        "enabled": _mod_enabled(mods, "post"),
                        "postType": {
                            "publicChatRooms": Communities.ModuleInfo(chat_mod),
                            "blog": Communities.ModuleInfo(blog_mod),
                            "poll": Communities.ModuleInfo(poll_mod),
                            "image": Communities.ModuleInfo(image_mod),
                            "question": Communities.ModuleInfo(question_mod),
                        },
                    },
                    "chat": {
                        "enabled": _mod_enabled(mods, "chat"),
                        "spamProtectionEnabled": _mod_field(
                            mods, "chat", "spamProtectionEnabled", True
                        ),
                        "avChat": {
                            "screeningRoomEnabled": av.get(
                                "screeningRoomEnabled", False
                            ),
                            "audioEnabled": av.get("audioEnabled", True),
                            "videoEnabled": av.get("videoEnabled", False),
                            "audio2Enabled": av.get("audio2Enabled", True),
                        },
                        "publicChat": Communities.ModuleInfo(chat_mod),
                    },
                    "ranking": {
                        "enabled": _mod_enabled(mods, "ranking"),
                        "leaderboardEnabled": _mod_enabled(mods, "leaderboard"),
                        "rankingTable": conf.get("rankingTable", RANKING_TABLE),
                        "leaderboardList": conf.get("leaderboardList", []),
                    },
                    "featured": {
                        "enabled": _mod_enabled(mods, "featured"),
                        "postEnabled": _mod_field(
                            mods,
                            "featured",
                            "postEnabled",
                            _mod_enabled(mods, "featured"),
                        ),
                        "memberEnabled": _mod_field(
                            mods,
                            "featured",
                            "memberEnabled",
                            _mod_enabled(mods, "featured"),
                        ),
                        "publicChatRoomEnabled": _mod_field(
                            mods,
                            "featured",
                            "publicChatRoomEnabled",
                            _mod_enabled(mods, "chat"),
                        ),
                        "layout": _mod_field(mods, "featured", "layout", 1),
                    },
                    "catalog": {
                        "enabled": _mod_enabled(mods, "catalog"),
                        "curationEnabled": _mod_field(
                            mods,
                            "catalog",
                            "curationEnabled",
                            _mod_enabled(mods, "catalog"),
                        ),
                    },
                    "sharedFolder": {
                        "enabled": _mod_enabled(mods, "sharedFolder"),
                        "uploadPrivilege": _mod_field(
                            mods, "sharedFolder", "uploadPrivilege", 2
                        ),
                        "albumManagePrivilege": _mod_field(
                            mods, "sharedFolder", "albumManagePrivilege", 2
                        ),
                    },
                    "influencer": {
                        "enabled": _mod_enabled(mods, "influencer"),
                        "maxVipNumbers": _mod_field(
                            mods, "influencer", "maxVipNumbers", 12
                        ),
                        "maxVipMonthlyFee": _mod_field(
                            mods, "influencer", "maxVipMonthlyFee", 500
                        ),
                        "lock": _mod_field(mods, "influencer", "lock", False),
                    },
                    "topicCategories": {
                        "enabled": _mod_enabled(mods, "topicCategories"),
                    },
                    "externalContent": {
                        "enabled": _mod_enabled(mods, "externalContent"),
                    },
                },
                "appearance": _build_appearance(conf),
            },
            "advancedSettings": {
                "pollMinFullBarVoteCount": adv.get("pollMinFullBarVoteCount", 10),
                "welcomeMessageEnabled": conf.get("welcomeMessageEnabled", False),
                "welcomeMessageText": conf.get("welcomeMessage", ""),
                "catalogEnabled": _mod_enabled(mods, "catalog"),
                "defaultRankingTypeInLeaderboard": adv.get(
                    "defaultRankingTypeInLeaderboard", 1
                ),
                "frontPageLayout": conf.get("frontPageLayout", 1),
            },
            "communityHeadList": data.get("communityHeadList", []),
            "promotionalMediaList": [MediaList.Item(data["coverUrl"])]
            if "coverUrl" in data
            else None,
        }

    """
    [TODO]
    configuration!
    """

    """
    [NOTE]
    This is what we need to implement later.
    Here are real examples what server sends.

    userAddedTopicList:
    {
      "topicId": 17328,
      "style": {
        "backgroundColor": "#ECCA41"
      },
      "name": "Аниме"
    }

    influencerList:
    basically, user with influencerInfo obj:
    {
      "pinned": false,
      "createdTime": "2024-05-01T21:53:14Z",
      "fansCount": 179,
      "monthlyFee": 20
    }

    themePack:
    wtf is hash and how it calculated
    {
        "themeColor": "#34754e",
        "themePackHash": "ea6f312f63cb8fedbe2145f7967d39cb", # ???
        "themePackRevision": 130,
        "themePackUrl": "http://theme.aminoapps.com/x156542274-rev130.ndthemepack"
    }

    communityHeadList:
    basically list with all admins there
    idk really why they need to do it, will not
    add it for now

    extensions:
    also idk why we need it for now
    {
        "communityNameAliases": "Anime,Аниме",
        "iTagIdList": [
            100006
        ]
    }
    """
