from __future__ import print_function
import os.path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/documents"]

# Replace with your Google Doc ID
DOCUMENT_ID = "1XVFtFBRmqkvzaRlfCNV3EGNv6LLSGG9Y91EEmHyfqZo"

def get_docs_service():
    creds = None
    # token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If there are no (valid) credentials, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("docs", "v1", credentials=creds)
    return service

def write_to_doc(text):
    service = get_docs_service()

    requests = [
        {
            "insertText": {
                "location": {"index": 1},  # index 1 = just after the start
                "text": text,
            }
        }
    ]

    result = service.documents().batchUpdate(
        documentId=DOCUMENT_ID, body={"requests": requests}
    ).execute()

    print("Text inserted!")

if __name__ == "__main__":
    write_to_doc("Hello from Python! 🎉\n")
