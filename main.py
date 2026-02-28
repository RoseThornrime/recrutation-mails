from aiogoogle import Aiogoogle
import asyncio

from src.mails import get_messages
import src.config as conf
from src.gemini import get_gemini, analyze_mail


async def main():
    config = conf.get_config("keys.yaml")
    user_creds = conf.get_user_creds(config)
    client_creds = conf.get_client_creds(config)
    conf.set_gemini_key(config)

    gemini = get_gemini()
    async with Aiogoogle(user_creds=user_creds, client_creds=client_creds) as google:
        gmail = await google.discover("gmail", "v1")

        messages = await get_messages(google, gmail)
        if not messages:
            print("No messages found.")
            return
        
        for message in messages[:1]:
            print(message["content"])
            print(await analyze_mail(message["topic"],
                                       message["content"],
                                       gemini))
            print(message["date"])


if __name__ == "__main__":
    asyncio.run(main())
