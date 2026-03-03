import collections

# small hack because backoff used python's older version
collections.Callable = collections.abc.Callable
import backoff
from aiogoogle.excs import HTTPError
from aiogoogle import Aiogoogle

from src.aliases import (SheetsClient, DriveClient, DriveFiles,
                         Spreadsheet, SheetValues, WorkMail)


HEADERS = ["Last update", "Company", "Position", "Status", "Action required"]


async def get_drive(google: Aiogoogle) -> DriveClient:
    """Get Google Drive client instance"""
    return await google.discover("drive", "v3")


async def get_sheets(google: Aiogoogle) -> SheetsClient:
    """Get Google Sheets client instance"""
    return await google.discover("sheets", "v4")


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def list_spreadsheets(google: Aiogoogle, drive: DriveClient
                            ) -> list[DriveFiles]:
    """Find all Google spreadsheets"""
    page_token = None
    files = []
    query = [
        "'me' in owners",
        "trashed=false",
        "mimeType='application/vnd.google-apps.spreadsheet'"
    ]
    while True:
        response = await google.as_user(
        (drive
            .files
            .list(q=" and ".join(query),
                fields="nextPageToken, files(id, name)",
                pageToken=page_token,)
        )
        )
        files.extend(response.get("files", []))
        page_token = response.get("nextPageToken", None)
        if page_token is None:
            return files


def get_first_page(sheet: Spreadsheet) -> str:
    """Get first page's title of the sheet"""
    return sheet["sheets"][0]["properties"]["title"]


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def get_spreadsheet(google: Aiogoogle, sheets: SheetsClient,
                          sheet_id: str) -> Spreadsheet:
    """Get spreadsheet from Google Sheets API"""
    return await google.as_user(
        sheets
        .spreadsheets
        .get(spreadsheetId=sheet_id)
    )


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def get_spreadsheet_values(google: Aiogoogle, sheets: SheetsClient,
                                 sheet_id: str) -> SheetValues:
    """Get values from the spreadsheet using Google Sheets API"""
    sheet = await get_spreadsheet(google, sheets, sheet_id)
    result = await google.as_user(
                sheets
                .spreadsheets                
                .values
                .get(spreadsheetId=sheet_id, range=get_first_page(sheet))
    )
    return result["values"][1:]


async def find_spreadsheet(google: Aiogoogle, drive: DriveClient,
                           title: str) -> str|None:
    """Find id of the spreadsheet with given id"""
    spreadsheets = await list_spreadsheets(google, drive)
    for file in spreadsheets:
        if file["name"] == title:
            return file["id"]
    return None


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def create_spreadsheet(google: Aiogoogle, sheets: SheetsClient,
                             title: str) -> str:
    """Create a new spreadsheet, return its id"""
    properties = {"properties": {"title": title}}
    result = await google.as_user(
        (sheets
         .spreadsheets
         .create(json=properties, fields="spreadsheetId"))
    )
    sheet_id = result["spreadsheetId"]
    sheet = await get_spreadsheet(google, sheets, sheet_id)
    first_page = get_first_page(sheet)
    await google.as_user(
            (sheets
            .spreadsheets
            .values
            .append(
                spreadsheetId=sheet_id,
                range=first_page,
                valueInputOption="USER_ENTERED",
                json={"values": [HEADERS,]}
            ))
        )
    return sheet_id


def are_texts_similiar(text1: str, text2: str) -> bool:
    """Check if two texts are similiar"""
    return text1.startswith(text2) or text2.startswith(text1)


def find_recrutation(sheet_data: SheetValues, company: str, position: str
                     ) -> int|None:
    """Find sheet row containing info about recrutation with given
    company and position"""
    for index, row in enumerate(sheet_data):
        _, row_company, row_position, _, _ = row
        if (are_texts_similiar(company, row_company)
            and are_texts_similiar(position, row_position)):
                return index
    return None


def update_data_locally(filtered_mails: list[WorkMail],
                        sheet_data: SheetValues
                        ) -> None:
    """Update statuses of recrutations, append new ones"""
    for mail in filtered_mails:
        index = find_recrutation(sheet_data, mail["company"],
                                 mail["position"])
        to_save = [
                mail["last_update"],
                mail["company"],
                mail["position"],
                mail["status"],
                mail["action"]
        ]
        if index is not None:
            sheet_data[index] = to_save
        else:
            sheet_data.append(to_save)


@backoff.on_exception(backoff.expo, HTTPError, max_tries=32)
async def update_data_sheet(google: Aiogoogle, sheets: SheetsClient,
                            sheet_data: SheetValues, sheet_id: str
                            ) -> None:
    """Update spreadsheet data using Google Sheets API,
    according to local values"""
    sheet = await get_spreadsheet(google, sheets, sheet_id)
    sheet_data = [HEADERS,] + sheet_data
    await google.as_user(
        sheets
        .spreadsheets
        .values
        .update(
            spreadsheetId=sheet_id,
            range=get_first_page(sheet),
            valueInputOption="USER_ENTERED",
            json={"values": sheet_data}
        )
    )
