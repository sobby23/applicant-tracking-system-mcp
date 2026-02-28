import base64
from email.message import EmailMessage
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# import environment variables from .env file
load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/spreadsheets',
]


def get_credentials():
    """Get valid user credentials (Gmail + Sheets). Re-run oauth if you add new scopes."""
    creds = None
    token_path = os.path.expanduser(os.getenv('GOOGLE_TOKEN_PATH'))
    credentials_path = os.path.expanduser(os.getenv('GOOGLE_CREDENTIALS_PATH'))

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"Credentials file not found at {credentials_path}")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds


def get_gmail_service():
    """Gets valid user credentials from storage and creates Gmail API service."""
    return build('gmail', 'v1', credentials=get_credentials())


def gmail_create_draft(recipient: str, subject: str, body: str):
    """Create and insert a draft email.
     Print the returned draft's message and id.
     Returns: Draft object, including draft id and message meta data.

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
    try:
        # create gmail api client
        service = get_gmail_service()

        message = EmailMessage()

        message.set_content(body)

        message["To"] = recipient
        message["From"] = os.getenv("USER_EMAIL")
        message["Subject"] = subject

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"message": {"raw": encoded_message}}
        # pylint: disable=E1101
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body=create_message)
            .execute()
        )

        print(f'Draft id: {draft["id"]}\nDraft message: {draft["message"]}')

    except HttpError as error:
        print(f"An error occurred: {error}")
        draft = None

    return draft


if __name__ == "__main__":
    gmail_create_draft()