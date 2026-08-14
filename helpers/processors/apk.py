from struct import unpack_from

from aiohttp import ClientSession

from helpers.processors.remotezip import RemoteZipProcessor

MANIFEST_NAME = b"AndroidManifest.xml"

RES_STRING_POOL = 0x0001
RES_XML_RESOURCE_MAP = 0x0180
RES_XML_START_ELEMENT = 0x0102
ATTR_VERSION_CODE = 0x0101021B
ATTR_VERSION_NAME = 0x0101021C
TYPE_STRING = 0x03
TYPE_INT_DEC = 0x10


class ApkProcessor:
    @staticmethod
    def _strings(chunk: bytes) -> list[str]:
        count, _styles, flags, start, _styles_start = unpack_from("<IIIII", chunk, 8)
        utf8 = bool(flags & (1 << 8))

        pool = []
        for i in range(count):
            (offset,) = unpack_from("<I", chunk, 28 + i * 4)
            at = start + offset

            if utf8:
                # two lengths in front of the value, utf16 one then byte one,
                # either of them can take a second byte
                length = chunk[at + 1]
                if length & 0x80:
                    length = ((length & 0x7F) << 8) | chunk[at + 2]
                    at += 1
                pool.append(chunk[at + 2 : at + 2 + length].decode("utf-8", "replace"))
            else:
                (length,) = unpack_from("<H", chunk, at)
                value = chunk[at + 2 : at + 2 + length * 2]
                pool.append(value.decode("utf-16-le", "replace"))
        return pool

    @staticmethod
    def _parse(data: bytes) -> tuple[int | None, str | None]:
        pool: list[str] = []
        resources: list[int] = []

        offset = 8  # skip the file header
        while offset + 8 <= len(data):
            chunk_type, header_size, chunk_size = unpack_from("<HHI", data, offset)
            if chunk_size < 8 or offset + chunk_size > len(data):
                break

            if chunk_type == RES_STRING_POOL:
                pool = ApkProcessor._strings(data[offset : offset + chunk_size])

            elif chunk_type == RES_XML_RESOURCE_MAP:
                # maps a string pool index to the resource id it stands for,
                # that is how an attribute is known to be android:versionCode
                count = (chunk_size - header_size) // 4
                resources = list(unpack_from(f"<{count}I", data, offset + header_size))

            elif chunk_type == RES_XML_START_ELEMENT:
                body = offset + header_size
                attr_start, attr_size, attr_count = unpack_from("<HHH", data, body + 8)

                code = name = None
                for i in range(attr_count):
                    at = body + attr_start + i * attr_size
                    _ns, index, raw, _size, _res0, value_type, value = unpack_from(
                        "<IIIHBBI", data, at
                    )
                    resource = resources[index] if index < len(resources) else 0

                    if resource == ATTR_VERSION_CODE and value_type == TYPE_INT_DEC:
                        code = value
                    elif resource == ATTR_VERSION_NAME:
                        at = value if value_type == TYPE_STRING else raw
                        name = pool[at] if at < len(pool) else None

                # the first element is always <manifest>, nothing below it matters
                return code, name

            offset += chunk_size
        return None, None

    @staticmethod
    async def Version(
        session: ClientSession, url: str
    ) -> tuple[int | None, str | None]:
        data = await RemoteZipProcessor.File(
            session, url, lambda name: name == MANIFEST_NAME
        )
        return ApkProcessor._parse(data) if data else (None, None)
