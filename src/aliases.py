from google import genai
import aiogoogle


GeminiClient = genai.client.AsyncClient
GmailClient = aiogoogle.resource.GoogleAPI
SheetsClient = aiogoogle.resource.GoogleAPI
DriveClient = aiogoogle.resource.GoogleAPI

Config = dict

Message = dict[str, str]
WorkMail = dict[str, str]
GmailMessage = dict
GmailLabels = dict[str, str|None]

DriveFiles = dict
Spreadsheet = dict
SheetValues = list[list[str]]