from base64 import urlsafe_b64decode
import email
import collections

# small hack because backoff used python's older version
collections.Callable = collections.abc.Callable
import backoff

from aiogoogle import Aiogoogle
from aiogoogle.excs import HTTPError
import asyncio


def extract_content(message):
    text = urlsafe_b64decode(
        message["raw"]
    ).decode("utf-8")
    parsed = email.message_from_string(text, policy=email.policy.default)
    if parsed.is_multipart():
        for part in parsed.walk():
            content_type = part.get_content_type()
            if content_type == "text/html" or content_type == "text/plain":
                return part.get_content()
        return ""
    return parsed.get_content()


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def get_message_details(google, gmail, message_id):
    message = await google.as_user(
            (gmail
             .users
             .messages
             .get(userId="me", id=message_id["id"], format="raw"))
            )
    return {
        "topic": message["snippet"],
        "content": extract_content(message)
    }


async def get_messages(google, gmail):
    results = await google.as_user(
        (gmail
         .users
         .messages
         .list(userId="me", labelIds=["INBOX"]))
    )
    message_ids = results.get("messages", [])
    message_tasks = []
    for message_id in message_ids:
        message_tasks.append(get_message_details(google, gmail, message_id))
    return await asyncio.gather(*message_tasks)
