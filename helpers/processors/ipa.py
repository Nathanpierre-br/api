from plistlib import loads

from aiohttp import ClientSession

from helpers.processors.remotezip import RemoteZipProcessor


class IpaProcessor:
    @staticmethod
    def _is_app_info(name: bytes) -> bool:
        parts = name.split(b"/")
        return (
            len(parts) == 3
            and parts[0] == b"Payload"
            and parts[1].endswith(b".app")
            and parts[2] == b"Info.plist"
        )

    @staticmethod
    async def Version(
        session: ClientSession, url: str
    ) -> tuple[int | None, str | None]:
        data = await RemoteZipProcessor.File(session, url, IpaProcessor._is_app_info)
        if not data:
            return None, None

        info = loads(data)  # usually a binary plist, plistlib eats both
        build = str(info.get("CFBundleVersion") or "")
        name = info.get("CFBundleShortVersionString") or None

        return (int(build) if build.isdigit() else None), name
