from aiohttp import ClientSession
from orjson import dumps, loads

from helpers.config import Config
from helpers.processors.cache import CacheProcessor
from objects.types import PlatformType
from services.updates import UpdateService, github_session

CACHE_PREFIX = "repo:"
FRESH_KEY = "feed"
STALE_KEY = "last_known_good"

SITE = Config.UPDATE_REPO_SITE
ICON = f"{SITE}/static/images/altamino.png"
TITLE = "AltAmino / Repository"

APPS = [
    {
        "repo": Config.UPDATE_GITHUB_REPO,
        "name": "AltAmino",
        "bundleIdentifier": "com.narvii.master",
        "developerName": "shaderw0lf",
        "subtitle": "Mod to interact with AltAmino servers.",
        "localizedDescription": (
            "Mod to interract with AltAmino, open-source project that revives "
            "Amino, social network made by Narvii and owned by Medialab. Bug "
            "fixes included!\n\nCheck out sources:\nhttps://github.com/altamino"
        ),
        "category": "Social",
    },
    {
        "repo": "alx0rr/AltTeam-App",
        "name": "AltTeam",
        "bundleIdentifier": "top.altamino.altteam",
        "developerName": "alx0rr",
        "subtitle": "AltAmino Community Manager.",
        "localizedDescription": (
            "Homebrew ACM for AltAmino, open-source project that revives Amino, "
            "social network made by Narvii and owned by Medialab.\n\nCheck out "
            "sources:\nhttps://github.com/alx0rr/AltTeam-App"
        ),
        "category": "Social",
    },
]


class RepositoryService:
    @staticmethod
    async def _build_app(session: ClientSession, app: dict) -> dict | None:
        meta = PlatformType.META[PlatformType.IOS]

        found = await UpdateService.latest(session, meta["suffix"], app["repo"])
        if found is None:
            return None

        release, asset = found
        url = asset["browser_download_url"]

        _code, version = await UpdateService.version(session, meta, url)
        if not version:
            return None

        return {
            **app,
            "version": version,
            "versionDate": release.get("published_at") or "",
            "versionDescription": UpdateService.notes(meta, release.get("body") or ""),
            "downloadURL": url,
            "size": asset.get("size") or 0,
        }

    @staticmethod
    def _build_altstore(apps: list[dict]) -> dict:
        return {
            "name": TITLE,
            "iconURL": ICON,
            "website": SITE,
            "apps": [
                {
                    "beta": False,
                    "name": app["name"],
                    "bundleIdentifier": app["bundleIdentifier"],
                    "developerName": app["developerName"],
                    "localizedDescription": app["localizedDescription"],
                    "version": app["version"],
                    "versionDate": app["versionDate"],
                    "versionDescription": app["versionDescription"],
                    "downloadURL": app["downloadURL"],
                    "subtitle": app["subtitle"],
                    "iconURL": ICON,
                    "tintColor": "000000",
                    "size": app["size"],
                }
                for app in apps
            ],
        }

    @staticmethod
    def _build_scarlet(apps: list[dict]) -> dict:
        return {
            "META": {"repoName": TITLE, "repoIcon": ICON},
            "Social": [
                {
                    "name": app["name"],
                    "version": app["version"],
                    "down": app["downloadURL"],
                    "category": app["category"],
                    "description": app["subtitle"],
                    "bundleID": app["bundleIdentifier"],
                    "appstore": app["bundleIdentifier"],
                }
                for app in apps
                if app["category"] == "Social"
            ],
        }

    @staticmethod
    async def feed(kind: str) -> dict | None:
        builder = {
            "altstore": RepositoryService._build_altstore,
            "scarlet": RepositoryService._build_scarlet,
        }.get(kind)
        if builder is None:
            return None

        fresh_key = f"{FRESH_KEY}:{kind}"
        stale_key = f"{STALE_KEY}:{kind}"

        cached = await CacheProcessor.Get(fresh_key, CACHE_PREFIX)
        if cached:
            return loads(cached)

        apps = []
        try:
            async with github_session() as session:
                for app in APPS:
                    built = await RepositoryService._build_app(session, app)
                    if built:
                        apps.append(built)
        except Exception:
            apps = []

        if len(apps) != len(APPS):
            stale = await CacheProcessor.Get(stale_key, CACHE_PREFIX)
            return loads(stale) if stale else None

        feed = builder(apps)
        payload = dumps(feed)
        await CacheProcessor.Make(
            fresh_key, payload, CACHE_PREFIX, Config.UPDATE_CACHE_TTL
        )
        await CacheProcessor.Make(stale_key, payload, CACHE_PREFIX)
        return feed
