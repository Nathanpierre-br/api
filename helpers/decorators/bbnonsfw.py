import asyncio
from base64 import b64decode, b64encode
from functools import wraps
from io import BytesIO
from typing import Literal
from httpx import AsyncClient
from PIL import Image
from helpers.config import Config
from objects.errors import Errors
from helpers.functions import detect_file_ext


def shrink_image_data_if_needed(
    image_data: str | bytes, max_size: int = 750
) -> str | bytes:
    image_bytes = None

    if isinstance(image_data, bytes):
        image_bytes = image_data
    elif isinstance(image_data, str):
        try:
            image_bytes = b64decode(image_data)
        except Exception:
            return image_data

    if not image_bytes:
        return image_data

    try:
        with Image.open(BytesIO(image_bytes)) as img:
            width, height = img.size
            if width > max_size or height > max_size:
                ratio = max_size / max(width, height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)

                resample_filter = getattr(Image, "Resampling", Image).LANCZOS
                img_format = img.format if img.format else "JPEG"
                if img_format == "GIF":
                    img_format = "JPEG"

                resized_img = img.resize(
                    (new_width, new_height), resample=resample_filter
                )
                if img_format == "JPEG" and resized_img.mode in ("RGBA", "LA", "P"):
                    resized_img = resized_img.convert("RGB")

                out_buffer = BytesIO()
                resized_img.save(out_buffer, format=img_format)
                resized_bytes = out_buffer.getvalue()

                image_bytes = resized_bytes
    except Exception as e:
        print(f"Error shrinking image: {e}")
        return image_data

    # if isinstance(image_bytes, str):
    #    return image_bytes
    return b64encode(image_bytes).decode()


async def bbnonsfw_manual_check(image: str | bytes) -> bool:
    """
    False if image is OK, True if NSFW.
    """

    if not Config.ENABLE_BBNONSFW:
        return False

    if isinstance(image, bytes):
        first_bytes = image[:128]
    elif isinstance(image, str):
        first_bytes = b64decode(image)[:128]
    else:
        raise Exception("Empty data")

    file_ext = detect_file_ext(first_bytes)
    if file_ext is None:
        return False

    image = await asyncio.to_thread(shrink_image_data_if_needed, image, 650)
    async with AsyncClient() as client:
        response = await client.post(
            Config.BBNONSFW_API_URL,
            json={"i": image},
            headers={
                "Authorization": f"Bearer {Config.BBNONSFW_API_KEY}",
            },
        )
        response.raise_for_status()

    answer = response.json()
    if not isinstance(answer, list):
        print(f"Unexpected API response format: {answer}")
        return False

    nsfw_score = next(
        (
            x["score"]
            for x in answer
            if isinstance(x, dict) and x.get("label") == "nsfw"
        ),
        0.0,
    )

    print(f"NSFW Score: {nsfw_score}")
    return nsfw_score > 0.87  # IS THAT THE BITE OF 87?! O_O


def bbnonsfw(
    target: Literal["body", "json"],
    key: str | None = None,
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not Config.ENABLE_BBNONSFW:
                return await func(*args, **kwargs)
            request = kwargs.get("request")
            if target == "body":
                body = b64encode(await request.body()).decode()
                if await bbnonsfw_manual_check(body):
                    return Errors.NSFWContent()
            return await func(*args, **kwargs)

        return wrapper

    return decorator
