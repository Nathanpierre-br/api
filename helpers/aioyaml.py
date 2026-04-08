import aiofiles
import yaml


async def aioyaml(path) -> dict:
    async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
        content = await f.read()
        return yaml.safe_load(content)
