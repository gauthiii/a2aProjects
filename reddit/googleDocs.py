from __future__ import print_function
import os.path
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------
# MCP SERVER SETUP
# ---------------------------------------------------------------------
mcp = FastMCP("Google Docs Server")

# ---------------------------------------------------------------------
# GOOGLE API CONFIG
# ---------------------------------------------------------------------
# note: Since we also change sharing permissions, we need DRIVE scope too.
# If you previously ran this with only Docs scope, DELETE token.json once.
SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive"
]

# Optional default Doc ID (can be overridden in function args)
DOCUMENT_ID = "1XVFtFBRmqkvzaRlfCNV3EGNv6LLSGG9Y91EEmHyfqZo"


# ---------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------
def get_current_date() -> str:
    """
    Returns the current date/time as a formatted string.
    """
    return datetime.now().strftime("%d %B %Y, %H:%M")


def get_credentials() -> Credentials:
    """
    Loads or creates OAuth credentials and returns a Credentials object.
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def get_docs_service():
    """
    Returns an authenticated Google Docs service.
    """
    creds = get_credentials()
    return build("docs", "v1", credentials=creds)


def get_drive_service():
    """
    Returns an authenticated Google Drive service.
    """
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)


# ---------------------------------------------------------------------
# TOOLS
# ---------------------------------------------------------------------
@mcp.tool()
def create_doc(title: str = "New Python Document") -> str:
    """
    Creates a new Google Doc, makes it publicly viewable (anyone with link),
    and returns the document ID as a string.
    """
    docs_service = get_docs_service()

    # Create the doc
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc.get("documentId")

    print(f"✅ Created new document: {title}")
    print(f"📄 Document ID: {doc_id}")

    # Make it public (anyone with the link can VIEW)
    drive_service = get_drive_service()
    permission = {
        "type": "anyone",
        "role": "reader",  # change to 'writer' if you ever want public edit (dangerous!)
    }

    drive_service.permissions().create(
        fileId=doc_id,
        body=permission
    ).execute()

    print("🌍 Document is now publicly viewable.")
    print(f"🔗 Public link: https://docs.google.com/document/d/{doc_id}/edit")

    # For MCP use, returning just the ID is fine; client can form URL if needed
    return doc_id


@mcp.tool()
def write_to_doc(text: str, id: str = DOCUMENT_ID) -> str:
    """
    Appends text to the end of the given Google Doc, prefixed with a timestamp.
    Returns the "message_added" and the "id" of this document.
    """
    service = get_docs_service()

    # Fetch document to find the end index
    doc = service.documents().get(documentId=id).execute()
    content = doc.get("body", {}).get("content", [])
    if not content:
        # Empty doc: index 1 is right after the implicit start
        end_index = 1
    else:
        end_index = content[-1].get("endIndex", 1) - 1

    requests = [
        {
            "insertText": {
                "location": {"index": end_index},
                "text": f"\n\n{get_current_date()}\n{text}",
            }
        }
    ]

    service.documents().batchUpdate(
        documentId=id,
        body={"requests": requests}
    ).execute()


    # msg = f"✅ Text appended to document ({id})"
    # print(msg)

    result = {
        "id" : id,
        "message_added": f"\n\n{get_current_date()}\n{text}"
    }
    return str(result)


@mcp.tool()
def read_doc(id: str = DOCUMENT_ID) -> str:
    """
    Reads the full plain-text content of the given Google Doc.
    Returns the "id" of the doc and the plain text "content".
    """
    service = get_docs_service()
    doc = service.documents().get(documentId=id).execute()
    content = doc.get("body", {}).get("content", [])

    text = ""
    for element in content:
        if "paragraph" in element:
            for elem in element["paragraph"]["elements"]:
                if "textRun" in elem:
                    text += elem["textRun"]["content"]

    print("\n📖 Document content:\n")
    print(text)

    result = {
        "id" : id,
        "content": text
    }

    return str(result)


# ---------------------------------------------------------------------
# MCP ENTRYPOINT
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Run as an MCP server (for Claude Desktop / A2A etc.)
    mcp.run(transport="stdio")

    # If you ever want to test directly instead of MCP, you can comment out
    # the line above and temporarily use:
    #
    # new_id = create_doc("Python Generated Doc")
    # print(new_id)
    # write_to_doc("This is a new doc", new_id)
    # read_doc(new_id)
    # x = write_to_doc("The movie is good")
    # print(x)
