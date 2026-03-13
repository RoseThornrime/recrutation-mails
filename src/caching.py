import aiofiles

from src.aliases import Message
from src.gemini import Analysis


async def save_message_ids(ids: list[str], path: str):
    """Save ids of cached gmail messages to a file"""
    async with aiofiles.open(path, "w") as f:
        await f.write("\n".join(ids))


async def read_message_ids(path: str) -> list[str]:
    "Read ids of cached gmail messages from a file"
    async with aiofiles.open(path, "a+") as f:
        await f.seek(0)
        return [line.rstrip() for line in await f.readlines()]


def get_noncached_mails(messages: list[Message], cached: list[str]
                        ) -> list[Message]:
    """Get mails that are not already cached"""
    return [msg for msg in messages[::-1] if msg["id"] not in cached]


def add_to_cache(analyses: list[Analysis], cached: list[str]) -> None:
    """Add analysed messages to cache"""
    for _, id_, _ in analyses:
        cached.append(id_)
