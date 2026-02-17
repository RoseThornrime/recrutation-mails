import os
from base64 import urlsafe_b64decode
import email
import time

from google import genai
from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import (UserCreds, ClientCreds)
import asyncio
import yaml


def get_user_creds(config):
    return UserCreds(
        access_token=config["user_creds"]["access_token"],
        refresh_token=config["user_creds"]["refresh_token"],
        expires_at=config["user_creds"]["expires_at"] or None,
    )


def get_client_creds(config):
    return ClientCreds(
        client_id=config["client_creds"]["client_id"],
        client_secret=config["client_creds"]["client_secret"],
        scopes=config["client_creds"]["scopes"],
    )


def set_gemini_key(config):
    os.environ["GEMINI_API_KEY"] = config["gemini_key"]


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


async def analyze_gemini(topic, content, gemini):
    model = "gemini-3-flash-preview"
    contents = (f"Is it work related? Answer shortly using format:",
                " 'work: <company name>' if yes, or 'no' otherwise.",
                f"The title to read is: '{topic}'.",
                f"The content to read is: '{content}.") 
    try:
        response = await gemini.models.generate_content(
            model=model,
            contents=contents
        )
    except genai.errors.ServerError as error:
        print(f"An error occurred: {error}")
    return response.text


async def main():
    with open("keys.yaml", "r") as stream:
        config = yaml.load(stream, Loader=yaml.FullLoader)

    user_creds = get_user_creds(config)
    client_creds = get_client_creds(config)

    set_gemini_key(config)
    gemini = genai.Client().aio
    async with Aiogoogle(user_creds=user_creds, client_creds=client_creds) as google:
        gmail = await google.discover("gmail", "v1")

        messages = await get_messages(google, gmail)
        if not messages:
            print("No messages found.")
            return
        
        for message in messages[:1]:
            print(await analyze_gemini(message["topic"],
                                       message["content"],
                                       gemini))
            # time.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
