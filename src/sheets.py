HEADERS = ["Last update", "Company", "Position", "Status", "Action required"]


async def get_drive(google):
    return await google.discover("drive", "v3")


async def get_sheets(google):
    return await google.discover("sheets", "v4")


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


async def get_spreadsheet(google, sheets, sheet_id):
    return await google.as_user(
        sheets
        .spreadsheets
        .get(spreadsheetId=sheet_id)
    )


async def get_spreadsheet_values(google, sheets, sheet_id):
    sheet = await get_spreadsheet(google, sheets, sheet_id)
    return await google.as_user(
                sheets
                .spreadsheets                
                .values
                .get(spreadsheetId=sheet_id, range=get_first_page(sheet))
    )


async def find_spreadsheet(google, drive, title):
    spreadsheets = await list_spreadsheets(google, drive)
    for file in spreadsheets:
        if file["name"] == title:
            return file["id"]
    return None


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
