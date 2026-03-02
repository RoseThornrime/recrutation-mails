import collections

# small hack because backoff used python's older version
collections.Callable = collections.abc.Callable
import backoff
from aiogoogle.excs import HTTPError


HEADERS = ["Last update", "Company", "Position", "Status", "Action required"]


async def get_drive(google):
    return await google.discover("drive", "v3")


async def get_sheets(google):
    return await google.discover("sheets", "v4")


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def list_spreadsheets(google, drive):
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


def get_first_page(sheet):
    return sheet["sheets"][0]["properties"]["title"]


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def get_spreadsheet(google, sheets, sheet_id):
    return await google.as_user(
        sheets
        .spreadsheets
        .get(spreadsheetId=sheet_id)
    )


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def get_spreadsheet_values(google, sheets, sheet_id):
    sheet = await get_spreadsheet(google, sheets, sheet_id)
    result = await google.as_user(
                sheets
                .spreadsheets                
                .values
                .get(spreadsheetId=sheet_id, range=get_first_page(sheet))
    )
    return result["values"][1:]


async def find_spreadsheet(google, drive, title):
    spreadsheets = await list_spreadsheets(google, drive)
    for file in spreadsheets:
        if file["name"] == title:
            return file["id"]
    return None


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def create_spreadsheet(google, sheets, title):
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


def find_recrutation(sheet_data, company, position):
    for index, row in enumerate(sheet_data):
        _, row_company, row_position, _, _ = row
        if company == row_company and row_position == position:
            return index
    return None


def update_data_locally(filtered_mails, sheet_data):
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


@backoff.on_exception(backoff.expo, HTTPError, max_tries=8)
async def update_data_sheet(google, sheets, sheet_data, sheet_id):
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
