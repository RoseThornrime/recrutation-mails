from base64 import urlsafe_b64decode
import email
from email.message import EmailMessage
import collections
from datetime import datetime

# small hack because backoff used python's older version
collections.Callable = collections.abc.Callable
import backoff
from aiogoogle.excs import HTTPError
import asyncio
from aiogoogle import Aiogoogle

from src.gemini import ApplicationStatus
from src.aliases import GmailClient, GmailMessage, Message, GmailLabels


async def get_gmail(google: Aiogoogle) -> GmailClient:
    """Get Gmail client instance"""
    return await google.discover("gmail", "v1")


def parse_mail(message: GmailMessage) -> EmailMessage:
    """Parse Gmail message into python email type"""
    text = urlsafe_b64decode(
        message["raw"]
    )
    try:
        text = text.decode("utf-8")
    except UnicodeDecodeError:
        text = text.decode("cp1252")
    return email.message_from_string(text, policy=email.policy.default)


def extract_content(parsed: EmailMessage) -> str:
    """Extract content from python email message"""
    if parsed.is_multipart():
        for part in parsed.walk():
            content_type = part.get_content_type()
            if content_type == "text/html" or content_type == "text/plain":
                return part.get_content()
        return ""
    return parsed.get_content()


def extract_date(parsed: EmailMessage) -> str:
    """Extract formatted date str from python email message"""
    date_str = parsed["date"]
    dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
    return formatted


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def get_message_details(google: Aiogoogle, gmail: GmailClient,
                               message_id: str) -> Message:
    """Load message details from Gmail API"""
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


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def get_messages(google: Aiogoogle, gmail: GmailClient
                       ) -> list[Message]:
    """List all messages from Gmail API"""
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


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def get_labels(google: Aiogoogle, gmail: GmailClient) -> GmailLabels:
    """Get ids of custom labels for job messages"""
    current_labels = await google.as_user(
            (gmail
             .users
             .labels
             .list(userId="me"))
            )
    wanted_labels = [f"work/{status.value}" for status in ApplicationStatus]
    result = {}
    for label in current_labels["labels"]:
        name = label["name"]
        if name in wanted_labels:
            result[name] = label["id"]
    for name in wanted_labels:
        if name not in result:
            result[name] = None
    return result


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def create_missing_labels(google: Aiogoogle, gmail: GmailClient,
                                labels: GmailLabels) -> None:
    """Create custom job labels if needed"""
    tasks = []
    for label_name, label_id in labels.items():
        if label_id:
            continue
        label_body = {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show"
        }
        task = google.as_user(
            gmail
            .users
            .labels
            .create(
                userId="me",
                json=label_body
            )
        )
        tasks.append(task)
    results = await asyncio.gather(*tasks)
    for label in results:
        if label["name"] in labels:
            labels["name"] = label["id"]


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def change_message_labels(google: Aiogoogle, gmail: GmailClient,
                                messages: list[Message],
                                possible_labels: GmailLabels
                                ) -> None:
    """Move messages from inbox to custom folders (using labels)"""
    grouped = collections.defaultdict(list)
    for message in messages:
        grouped[message["status"]].append(message["id"])
    tasks = []
    for status, message_ids in grouped.items():
        label_name = f"work/{status}"
        label_id = possible_labels[label_name]
        body = {
            "ids": message_ids,
            "addLabelIds": [label_id],
            "removeLabelIds": ["INBOX"]
        }
        task = google.as_user(
            gmail
            .users
            .messages
            .batchModify(
                userId="me",
                json=body
            )
        )
        tasks.append(task)
    await asyncio.gather(*tasks)
