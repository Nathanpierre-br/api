from struct import unpack_from
from typing import Callable
from zlib import decompress

from aiohttp import ClientSession

EOCD_SIGNATURE = b"PK\x05\x06"
EOCD_MAX_SIZE = 65557  # 22 byte record + 64kb of possible trailing comment
CENTRAL_DIRECTORY_SIGNATURE = 0x02014B50
DEFLATED = 8


class RemoteZipProcessor:
    @staticmethod
    async def _range(
        session: ClientSession, url: str, header: str
    ) -> tuple[bytes, str]:
        async with session.get(url, headers={"range": f"bytes={header}"}) as response:
            if response.status != 206:
                raise ValueError(f"no range support, got {response.status}")
            return await response.read(), response.headers.get("content-range", "")

    @staticmethod
    async def _entry(
        session: ClientSession, url: str, match: Callable[[bytes], bool]
    ) -> tuple[int, int, int] | None:
        # github's asset cdn answers 501 to suffix ranges (`bytes=-N`), so ask
        # for a single byte first just to learn the size from content-range
        _, content_range = await RemoteZipProcessor._range(session, url, "0-0")
        size = int(content_range.rsplit("/", 1)[-1])

        tail, _ = await RemoteZipProcessor._range(
            session, url, f"{max(0, size - EOCD_MAX_SIZE)}-{size - 1}"
        )

        eocd = tail.rfind(EOCD_SIGNATURE)
        if eocd == -1:
            return None

        directory_size, directory_offset = unpack_from("<II", tail, eocd + 12)
        if directory_offset + directory_size > size:
            return None  # zip64, not something an app package realistically hits

        directory, _ = await RemoteZipProcessor._range(
            session, url, f"{directory_offset}-{directory_offset + directory_size - 1}"
        )

        offset = 0
        while offset + 46 <= len(directory):
            if unpack_from("<I", directory, offset)[0] != CENTRAL_DIRECTORY_SIGNATURE:
                break

            (method,) = unpack_from("<H", directory, offset + 10)
            (compressed,) = unpack_from("<I", directory, offset + 20)
            name_length, extra_length, comment_length = unpack_from(
                "<HHH", directory, offset + 28
            )
            (local_offset,) = unpack_from("<I", directory, offset + 42)

            if match(directory[offset + 46 : offset + 46 + name_length]):
                return local_offset, compressed, method

            offset += 46 + name_length + extra_length + comment_length
        return None

    @staticmethod
    async def File(
        session: ClientSession, url: str, match: Callable[[bytes], bool]
    ) -> bytes | None:
        entry = await RemoteZipProcessor._entry(session, url, match)
        if entry is None:
            return None

        local_offset, compressed, method = entry

        # only the local header knows its own length
        header, _ = await RemoteZipProcessor._range(
            session, url, f"{local_offset}-{local_offset + 29}"
        )
        name_length, extra_length = unpack_from("<HH", header, 26)

        start = local_offset + 30 + name_length + extra_length
        body, _ = await RemoteZipProcessor._range(
            session, url, f"{start}-{start + compressed - 1}"
        )
        return decompress(body, -15) if method == DEFLATED else body
