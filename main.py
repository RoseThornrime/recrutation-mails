from aiogoogle import Aiogoogle
import asyncio
from aiogoogle.excs import HTTPError
from aiohttp.client_exceptions import ClientConnectorDNSError

import src.config as cfg
import src.gemini as ai
import src.mails as mails
import src.sheets as gsheets
import src.caching as cache
import src.aliases as aliases


CACHE_PATH = "mails_cache.txt"


async def start_spreadsheet(config: aliases.Config, google: Aiogoogle,
                             drive: aliases.DriveClient,
                             sheets: aliases.SheetsClient) -> str:
    """Finds the spreadsheet and creates one if not found"""
    sheet_name = cfg.get_sheet_name(config)
    sheet_id = await gsheets.find_spreadsheet(google, drive,
                                                sheet_name)
    if sheet_id is None:
        sheet_id = await gsheets.create_spreadsheet(google, sheets,
                                                    sheet_name)
    return sheet_id


async def update_spreadsheet(google: Aiogoogle, sheets: aliases.SheetsClient,
                             sheet_id: str, work_mails: list[aliases.WorkMail]
                             ) -> None:
    """Updates data in the spreadsheet"""
    spreadsheet = await gsheets.get_spreadsheet_values(google, sheets,
                                                            sheet_id)
    gsheets.update_data_locally(work_mails, spreadsheet)
    await gsheets.update_data_sheet(google, sheets, spreadsheet,
                                    sheet_id)
    print("Spreadsheet updated")


async def move_mails(google: Aiogoogle, gmail: aliases.GmailClient,
                     work_mails: list[aliases.WorkMail]) -> None:
    """Move mails from inbox using the label system"""
    possible_labels = await mails.get_labels(google, gmail)
    await mails.create_missing_labels(google, gmail, possible_labels)
    await mails.change_message_labels(google, gmail, work_mails,
                                        possible_labels)
    print("Work mails moved")


async def get_clients(google: Aiogoogle, config: aliases.Config
                      ) -> tuple[aliases.GmailClient, aliases.SheetsClient,
                                aliases.DriveClient, aliases.GeminiClient]:
    """Get instances of all used API clients"""
    gmail = await mails.get_gmail(google)
    sheets = await gsheets.get_sheets(google)
    drive = await gsheets.get_drive(google)
    cfg.set_gemini_key(config)
    gemini = ai.get_gemini()
    return gmail, sheets, drive, gemini


def get_noncached_mails(messages: list[aliases.Message], cached: list[str]
                        ) -> list[aliases.Message]:
    """Get mails that are not already cached"""
    return [msg for msg in messages[::-1] if msg["id"] not in cached]
    

async def main():
    messages = []
    cached = await cache.read_message_ids(CACHE_PATH)
    config = await cfg.get_config("keys.yaml")
    user_creds = cfg.get_user_creds(config)
    client_creds = cfg.get_client_creds(config)
    try:
        async with Aiogoogle(user_creds=user_creds,
                             client_creds=client_creds) as google:
            gmail, sheets, drive, gemini = await get_clients(google, config)
            sheet_id = await start_spreadsheet(config, google, drive, sheets)
            messages = await mails.get_messages(google, gmail)
            print(f"Messages in inbox: {len(messages)}")
            if not messages:
                print("No messages found")
                return
            messages = get_noncached_mails(messages, cached)
            print(f"New messages found: {len(messages)}")
            analyses = await ai.analyze_mails(messages, gemini)
            work_mails = ai.filter_mails(analyses, messages)
            print(f"Job-related messages found: {len(work_mails)}")
            if not work_mails:
                print("No job-related messages found")
                return
            await update_spreadsheet(google, sheets, sheet_id, work_mails)
            await move_mails(google, gmail, work_mails)
    except (HTTPError, ClientConnectorDNSError) as e:
        print(f"Error found: {e}")
        return
    cached.extend([msg["id"] for msg in messages])
    await cache.save_message_ids(cached, CACHE_PATH)


if __name__ == "__main__":
    asyncio.run(main())
