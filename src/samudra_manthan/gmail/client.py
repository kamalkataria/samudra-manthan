from googleapiclient.discovery import build

from .auth import authenticate_gmail


def get_gmail_service():
    """Create and return an authenticated Gmail API service."""

    credentials = authenticate_gmail()

    return build(
        "gmail",
        "v1",
        credentials=credentials,
    )