from base64 import b64encode
from functools import wraps
from typing import Literal
from httpx import AsyncClient
from helpers.config import Config
from objects.errors import Errors

async def bbnonsfw_manual_check(image: str | bytes) -> bool:
    """
    False if image is OK, True if NSFW.
    """
    #this shit always get bad request from BBNONSFW_API_URL
    """
    if not Config.ENABLE_BBNONSFW:
        return False
        
    if isinstance(image, bytes):
        try:
            image = image.decode()
        except Exception:
            image = b64encode(image).decode()
            
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
        (x["score"] for x in answer if isinstance(x, dict) and x.get("label") == "nsfw"), 0.0
    )
    
    print(f"NSFW Score: {nsfw_score}")
    return nsfw_score > 0.9
    """
    return False

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