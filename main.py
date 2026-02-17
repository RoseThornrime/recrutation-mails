import os.path
from base64 import urlsafe_b64decode
import email
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google import genai

from dotenv import load_dotenv

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]



def get_credentials():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.valid:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def extract_content(message):
    text = urlsafe_b64decode(
        message["raw"]
    ).decode("utf-8")
    parsed = email.message_from_string(text, policy=email.policy.default)
    if parsed.is_multipart():
        for part in parsed.walk():
            content_type = part.get_content_type()
            if content_type == "text/html" or content_type == "text/plain":
                return part.get_content()
        return ""
    return parsed.get_content()


def get_messages(gmail_service):
    # Call the Gmail API
    results = (
        (gmail_service
            .users()
            .messages()
            .list(userId="me", labelIds=["INBOX"])
            .execute())
    )
    message_ids = results.get("messages", [])
    message_details = []
    for message_id in message_ids:
        message = (gmail_service
            .users()
            .messages()
            .get(userId="me", id=message_id["id"], format="raw")
            .execute())
        message_details.append(
            {
                "topic": message["snippet"],
                "content": extract_content(message)
            }
        )
    return message_details


def analyze_gemini(topic, content, client):
    model = "gemini-2.0-flash-lite"
    contents = (f"Is it work related? Answer shortly using format:",
                " 'work: <company name>' if yes, or 'no' otherwise.",
                f"The title to read is: '{topic}'.",
                f"The content to read is: '{content}.") 
    try:
        response = client.models.generate_content(
            model=model,
            contents=contents
        )
    except genai.errors.ServerError as error:
        print(f"An error occurred: {error}")
    return response.text


def main():
    load_dotenv() 
    creds = get_credentials()

    gmail_service = build("gmail", "v1", credentials=creds)

    client = genai.Client()


    try:
        messages = get_messages(gmail_service)
        if not messages:
            print("No messages found.")
            return
        
        for message in messages:
            print(analyze_gemini(message["topic"], message["content"], client))
            time.sleep(5)

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()