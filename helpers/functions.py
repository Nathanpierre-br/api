from fastapi import Request
from hashlib import blake2s
from base64 import b85decode, b85encode
from .generator import Generator


def parse_page_token(pageToken: str | None, start: int) -> int:
    """
    start param is important since it will fallback to it when pagetoken is invalid
    """

    try:
        decoded = b85decode(pageToken).decode()
        return max(0, int(decoded) if decoded.isdigit() else 0)
    except Exception:
        return start


def calculate_page_tokens(start: int, size: int, data: list) -> dict:
    """
    data param is important since
    if there is no data or len(data) < size
    it will return empty nextPageToken
    to stop infinite loop of getting data
    """
    prevPageCalc = "0" if start - size <= 0 else str(start - size)
    nextPageCalc = str(size + start)

    return {
        "prevPageToken": str2b85(prevPageCalc),
        "nextPageToken": None if len(data) < size else str2b85(nextPageCalc),
    }


def str2b85(data: str) -> str:
    return b85encode(data.encode()).decode()


def get_ip(request: Request) -> str:
    """since our servers under cloudflare, we need CF-Connecting-IP instead of X-Forwarded-For"""
    return request.headers.get("CF-Connecting-IP") or request.client.host or "1.1.1.1"


def get_hashed_ip(request: Request) -> str:
    return make_hash(get_ip(request), salt=b"ip")


def make_hash(*args: str | bytes, salt: bytes = None, need_salt: bool = False):
    """
    pass any data that string or bytes to make hash
    salt is max 8 bytes long
    """
    to_hash = b"".join(
        [item if isinstance(item, bytes) else item.encode() for item in args]
    )
    if need_salt and not salt:
        salt = Generator.Bytes(4)

    if salt:
        return blake2s(to_hash, salt=salt).hexdigest()
    return blake2s(to_hash).hexdigest()
