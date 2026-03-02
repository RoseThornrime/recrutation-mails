from base64 import urlsafe_b64decode
import email
import collections
from datetime import datetime

# small hack because backoff used python's older version
collections.Callable = collections.abc.Callable
import backoff
from aiogoogle.excs import HTTPError
import asyncio


async def get_gmail(google):
    return await google.discover("gmail", "v1")


def parse_mail(message):
    text = urlsafe_b64decode(
        message["raw"]
    ).decode("utf-8")
    return email.message_from_string(text, policy=email.policy.default)


def extract_content(parsed):
    if parsed.is_multipart():
        for part in parsed.walk():
            content_type = part.get_content_type()
            if content_type == "text/html" or content_type == "text/plain":
                return part.get_content()
        return ""
    return parsed.get_content()


def extract_date(parsed):
    date_str = parsed["date"]
    dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
    return formatted


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def get_message_details(google, gmail, message_id):
    message = await google.as_user(
            (gmail
             .users
             .messages
             .get(userId="me", id=message_id["id"], format="raw"))
            )
    parsed = parse_mail(message)
    return {
        "id": message_id["id"],
        "topic": message["snippet"],
        "content": extract_content(parsed),
        "date": extract_date(parsed)
    }


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def get_messages(google, gmail):
    message_ids = []
    page_token = None
    while True:
        results = await google.as_user(
            gmail
            .users
            .messages
            .list(
                userId="me",
                labelIds=["INBOX"],
                pageToken=page_token
            )
        )
        message_ids.extend(results.get("messages", []))
        page_token = results.get("nextPageToken")
        if not page_token:
            break
    message_tasks = []
    for message_id in message_ids:
        message_tasks.append(get_message_details(google, gmail, message_id))
    return await asyncio.gather(*message_tasks)


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def change_labels(google, gmail, messages):
    tasks = []
    for message in messages:
        body = {
            "addLabelIds": f"work: {message["status"]}",
            "removeLabelIds": "INBOX"
        }
        task = google.as_user(
            gmail
            .users
            .messages
            .modify(userId="me",
                    id=message["id"],
                    json=body)
        )
        tasks.append(task)
    await asyncio.gather(*tasks)
