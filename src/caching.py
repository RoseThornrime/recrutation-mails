import aiofiles


async def save_message_ids(ids: list[str], path: str):
    """Save ids of cached gmail messages to a file"""
    async with aiofiles.open(path, "w") as f:
        await f.write("\n".join(ids))


async def read_message_ids(path: str) -> list[str]:
    "Read ids of cached gmail messages from a file"
    async with aiofiles.open(path, "a+") as f:
        await f.seek(0)
        return [line.rstrip() for line in await f.readlines()]
