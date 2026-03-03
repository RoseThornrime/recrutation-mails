from aiogoogle import Aiogoogle
import asyncio
from aiogoogle.excs import HTTPError
from google.genai.errors import ClientError, ServerError
from aiohttp.client_exceptions import ClientConnectorDNSError

import src.config as cfg
import src.gemini as ai
import src.mails as mails
import src.sheets as gsheets
import src.caching as cache


async def main():
    try:
        path = "mails_cache.txt"
        cached = await cache.read_message_ids(path)
        config = cfg.get_config("keys.yaml")
        user_creds = cfg.get_user_creds(config)
        client_creds = cfg.get_client_creds(config)
        cfg.set_gemini_key(config)

        gemini = ai.get_gemini()
        async with Aiogoogle(user_creds=user_creds,
                             client_creds=client_creds) as google:
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
                print("No messages found")
                return
                        
            messages = [msg for msg in messages[::-1]
                        if msg["id"] not in cached]
            cached.extend([msg["id"] for msg in messages])
            await cache.save_message_ids(cached, path)

            analyses = await ai.analyze_mails(messages, gemini)
            work_mails = ai.filter_mails(analyses, messages)
            print(f"Job-related messages found: {len(work_mails)}")
            if not work_mails:
                print("No job-related messages found")
                return

            spreadsheet = await gsheets.get_spreadsheet_values(google, sheets,
                                                            sheet_id)
            gsheets.update_data_locally(work_mails, spreadsheet)
            await gsheets.update_data_sheet(google, sheets, spreadsheet,
                                            sheet_id)
            print("Spreadsheet updated")

            possible_labels = await mails.get_labels(google, gmail)
            await mails.create_missing_labels(google, gmail, possible_labels)
            await mails.change_message_labels(google, gmail, work_mails,
                                              possible_labels)
            print("Work mails moved")
    except (HTTPError, UnboundLocalError, ClientError, ServerError,
            ClientConnectorDNSError) as e:
        print(f"Error found: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())
