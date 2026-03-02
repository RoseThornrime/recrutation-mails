from aiogoogle import Aiogoogle
import asyncio
from aiogoogle.excs import HTTPError
from google.genai.errors import ClientError

import src.config as cfg
import src.gemini as ai
import src.mails as mails
import src.sheets as gsheets


async def main():
    try:
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
            print(f"Messages found: {len(messages)}")
            if not messages:
                print("No messages found.")
                return
            
            messages = messages[::-1]
            analyses_num = 10
            analyses = await ai.analyze_mails(messages[:analyses_num], gemini)
            work_mails = ai.filter_mails(analyses, messages[:analyses_num])
            print(f"Job-related messages found: {len(work_mails)}")
            if not work_mails:
                print("No work messages found.")

            spreadsheet = await gsheets.get_spreadsheet_values(google, sheets,
                                                            sheet_id)
            gsheets.update_data_locally(work_mails, spreadsheet)
            await gsheets.update_data_sheet(google, sheets, spreadsheet, sheet_id)
            print("Spreadsheet updated")
            await mails.change_labels(google, gmail, work_mails)
            print("Work mails moved")
    except (HTTPError, UnboundLocalError, ClientError) as e:
        print(f"Error found: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())
