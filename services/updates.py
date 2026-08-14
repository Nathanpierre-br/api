from hashlib import sha1
from re import M, finditer, search, sub

from aiohttp import ClientSession, ClientTimeout
from orjson import dumps, loads

from helpers.config import Config
from helpers.processors.apk import ApkProcessor
from helpers.processors.cache import CacheProcessor
from helpers.processors.ipa import IpaProcessor
from objects.types import PlatformType

CACHE_PREFIX = "update:"
FRESH_KEY = "latest"  # expires, that is what triggers a refetch
STALE_KEY = "last_known_good"  # never expires, used when github is down
ASSET_KEY = "asset:"  # never expires, an asset url always holds the same build
RELEASES_KEY = "releases:"  # shared by every platform and feed of one repo

TIMEOUT = ClientTimeout(total=20)
RELEASE_SCAN = 30

READERS = {
    PlatformType.ANDROID: ApkProcessor.Version,
    PlatformType.IOS: IpaProcessor.Version,
}


def github_session() -> ClientSession:
    headers = {
        "accept": "application/vnd.github+json",
        "user-agent": "AltAmino Open Server",
    }
    if Config.UPDATE_GITHUB_TOKEN:
        headers["authorization"] = f"Bearer {Config.UPDATE_GITHUB_TOKEN}"

    return ClientSession(timeout=TIMEOUT, headers=headers)


class UpdateService:
    @staticmethod
    def marker(
        meta: dict, body: str, name: str, value: str, shared: bool = True
    ) -> str | None:
        prefix = meta["marker"]
        names = [prefix + name[0].upper() + name[1:]] if prefix else [name]
        if shared and prefix:
            names.append(name)

        for marker in names:
            found = search(rf"^\s*{marker}\s*[:=]\s*({value})\s*$", body, flags=M)
            if found:
                return found.group(1).strip()
        return None

    @staticmethod
    def notes(meta: dict, body: str) -> str:
        written = UpdateService.marker(meta, body, "updateMessage", r".+")
        if written:
            return written

        text = body
        headings = list(finditer(r"^[ \t]{0,3}#{1,6}[ \t]*(.+)$", body, flags=M))
        for i, heading in enumerate(headings):
            if meta["name"] in heading.group(1).lower():
                end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
                text = body[heading.end() : end]
                break

        return sub(r"^\s*\*\*Full Changelog\*\*.*$", "", text, flags=M).strip()

    @staticmethod
    def asset(release: dict, suffix: str) -> dict | None:
        for asset in release.get("assets") or []:
            name = (asset.get("name") or "").lower()
            if name.endswith(suffix) and asset.get("browser_download_url"):
                return asset
        return None

    @staticmethod
    async def releases(session: ClientSession, repo: str | None = None) -> list[dict]:
        repo = repo or Config.UPDATE_GITHUB_REPO

        cached = await CacheProcessor.Get(RELEASES_KEY + repo, CACHE_PREFIX)
        if cached:
            return loads(cached)

        async with session.get(
            f"https://api.github.com/repos/{repo}/releases",
            params={"per_page": str(RELEASE_SCAN)},
        ) as response:
            if response.status != 200:
                return []
            releases = await response.json()

        await CacheProcessor.Make(
            RELEASES_KEY + repo, dumps(releases), CACHE_PREFIX, Config.UPDATE_CACHE_TTL
        )
        return releases

    @staticmethod
    async def latest(
        session: ClientSession, suffix: str, repo: str | None = None
    ) -> tuple[dict, dict] | None:
        # a release does not always carry a build for every platform, so the
        # newest release and the newest apk are not necessarily the same one
        for release in await UpdateService.releases(session, repo):
            if release.get("draft") or release.get("prerelease"):
                continue
            asset = UpdateService.asset(release, suffix)
            if asset:
                return release, asset
        return None

    @staticmethod
    async def version(
        session: ClientSession, meta: dict, url: str
    ) -> tuple[int | None, str | None]:
        key = ASSET_KEY + sha1(url.encode()).hexdigest()

        cached = await CacheProcessor.Get(key, CACHE_PREFIX)
        if cached:
            code, name = loads(cached)
            return code, name

        code, name = await READERS[meta["name"]](session, url)
        if code is not None:
            await CacheProcessor.Make(key, dumps([code, name]), CACHE_PREFIX)
        return code, name

    @staticmethod
    async def _build_manifest(
        session: ClientSession, meta: dict, release: dict, asset: dict
    ) -> dict | None:
        url = asset["browser_download_url"]
        body = release.get("body") or ""

        name = None
        override = UpdateService.marker(meta, body, "versionCode", r"\d+", False)
        if override:
            code = int(override)
        else:
            code, name = await UpdateService.version(session, meta, url)

        if code is None:
            return None

        return {
            "versionCode": code,
            "versionName": name or release.get("tag_name") or "",
            "url": url,
            "page": UpdateService.marker(meta, body, "updatePage", r"\S+")
            or Config.UPDATE_PAGE_URL,
            "message": UpdateService.marker(meta, body, "updateMessage", r".+") or "",
        }

    @staticmethod
    async def manifest(platform: str = PlatformType.ANDROID) -> dict:
        meta = PlatformType.resolve(platform)
        if meta is None:
            return {}

        fresh_key = f"{FRESH_KEY}:{meta['name']}"
        stale_key = f"{STALE_KEY}:{meta['name']}"

        cached = await CacheProcessor.Get(fresh_key, CACHE_PREFIX)
        if cached:
            return loads(cached)

        manifest = None
        try:
            async with github_session() as session:
                found = await UpdateService.latest(session, meta["suffix"])
                if found:
                    manifest = await UpdateService._build_manifest(
                        session, meta, *found
                    )
        except Exception:
            # rate limit, timeout, github outage
            manifest = None

        if manifest is None:
            stale = await CacheProcessor.Get(stale_key, CACHE_PREFIX)
            return loads(stale) if stale else {}

        payload = dumps(manifest)
        await CacheProcessor.Make(
            fresh_key, payload, CACHE_PREFIX, Config.UPDATE_CACHE_TTL
        )
        await CacheProcessor.Make(stale_key, payload, CACHE_PREFIX)
        return manifest
