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
        sheet_id = await gsheets.find_spreadsheet(google, drive,
                                                    sheet_name)
        if sheet_id is None:
            sheet_id = await gsheets.create_spreadsheet(google, sheets,
                                                           sheet_name)

        messages = await mails.get_messages(google, gmail)
        if not messages:
            print("No messages found.")
            return
        
        analyses = await ai.analyze_mails(messages[8:9], gemini)
        work_mails = ai.filter_mails(analyses, messages[8:9])
        spreadsheet = await gsheets.get_spreadsheet_values(google, sheets,
                                                           sheet_id)
        gsheets.update_data_locally(work_mails, spreadsheet)
        await gsheets.update_data_sheet(google, sheets, spreadsheet, sheet_id)


if __name__ == "__main__":
    asyncio.run(main())
