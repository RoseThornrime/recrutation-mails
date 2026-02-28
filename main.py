from aiogoogle import Aiogoogle
import asyncio

import src.config as cfg
import src.gemini as ai
import src.mails as mails
import src.sheets as gsheets


async def main():
    config = cfg.get_config("keys.yaml")
    user_creds = cfg.get_user_creds(config)
    client_creds = cfg.get_client_creds(config)
    cfg.set_gemini_key(config)

    gemini = ai.get_gemini()
    async with Aiogoogle(user_creds=user_creds, client_creds=client_creds) as google:
        gmail = await mails.get_gmail(google)
        sheets = await gsheets.get_sheets(google)
        drive = await gsheets.get_drive(google)

        sheet_name = cfg.get_sheet_name(config)
        spreadsheet = await gsheets.find_spreadsheet(google, drive,
                                                    sheets, sheet_name)
        if spreadsheet is None:
            spreadsheet = await gsheets.create_spreadsheet(google, sheets,
                                                           sheet_name)
        print(spreadsheet)

        # messages = await src.get_messages(google, gmail)
        # if not messages:
        #     print("No messages found.")
        #     return
        
        # for message in messages[:1]:
        #     print(message["content"])
        #     analysis = await src.analyze_mail(message["topic"],
        #                                message["content"],
        #                                gemini)
        #     print(analysis.is_recrutation)
        #     print(message["date"])


if __name__ == "__main__":
    asyncio.run(main())
