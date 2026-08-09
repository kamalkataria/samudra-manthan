from pathlib import Path
import json
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    # "https://www.googleapis.com/auth/gmail.modify",
    "https://mail.google.com/",
]


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CONFIG_DIR = (
    PROJECT_ROOT
    / "config"
)

CREDENTIALS_FILE = (
    CONFIG_DIR
    / "credentials.json"
)

TOKENS_DIR = (
    CONFIG_DIR
    / "tokens"
)

SELECTED_ACCOUNT_FILE = (
    CONFIG_DIR
    / "selected_account"
)


# ---------------------------------------------------------
# ACCOUNT NAME
# ---------------------------------------------------------

def account_filename(
    account: str,
) -> str:
    """
    Convert a Gmail address into a safe filename.

    Example:
        user@gmail.com
        ->
        user_gmail.com
    """

    return re.sub(
        r"[^a-zA-Z0-9_.-]",
        "_",
        account.strip().lower(),
    )


def get_token_file(
    account: str,
) -> Path:
    """Return the token file for a Gmail account."""

    return (
        TOKENS_DIR
        / f"{account_filename(account)}.json"
    )


# ---------------------------------------------------------
# SELECTED ACCOUNT
# ---------------------------------------------------------

def save_selected_account(
    account: str,
) -> None:
    """Remember which Gmail account is currently selected."""

    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    SELECTED_ACCOUNT_FILE.write_text(
        account.strip().lower() + "\n",
        encoding="utf-8",
    )


def get_selected_account() -> str | None:
    """Return the currently selected Gmail account."""

    if not SELECTED_ACCOUNT_FILE.exists():
        return None

    account = (
        SELECTED_ACCOUNT_FILE
        .read_text(
            encoding="utf-8",
        )
        .strip()
    )

    return account or None


def clear_selected_account() -> None:
    """Clear the currently selected Gmail account."""

    if SELECTED_ACCOUNT_FILE.exists():
        SELECTED_ACCOUNT_FILE.unlink()


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

def authenticate_gmail(
    force_login: bool = False,
) -> Credentials:
    """
    Authenticate the currently selected Gmail account.

    If force_login=True, Google OAuth login is performed
    and the resulting account becomes the selected account.
    """

    # -----------------------------------------------------
    # FORCE NEW LOGIN
    # -----------------------------------------------------

    if force_login:

        if not CREDENTIALS_FILE.exists():
            raise FileNotFoundError(
                "Google OAuth credentials not found:\n"
                f"  {CREDENTIALS_FILE}"
            )

        flow = (
            InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES,
            )
        )

        credentials = flow.run_local_server(
            port=0,
            access_type="offline",
            prompt="select_account",
        )

        service = build(
            "gmail",
            "v1",
            credentials=credentials,
        )

        profile = (
            service.users()
            .getProfile(
                userId="me"
            )
            .execute()
        )

        account = profile["emailAddress"]

        TOKENS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        token_file = get_token_file(
            account
        )

        token_file.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

        save_selected_account(
            account
        )

        return credentials

    # -----------------------------------------------------
    # LOAD SELECTED ACCOUNT
    # -----------------------------------------------------

    account = get_selected_account()

    if not account:
        raise RuntimeError(
            "No Gmail account is currently selected. "
            "Use login_gmail() first."
        )

    token_file = get_token_file(
        account
    )

    if not token_file.exists():
        raise RuntimeError(
            "No OAuth token found for the selected "
            f"Gmail account: {account}\n"
            "Use login_gmail() first."
        )

    credentials = (
        Credentials.from_authorized_user_file(
            token_file,
            SCOPES,
        )
    )

    # -----------------------------------------------------
    # VALID TOKEN
    # -----------------------------------------------------

    if credentials.valid:
        return credentials

    # -----------------------------------------------------
    # REFRESH TOKEN
    # -----------------------------------------------------

    if (
        credentials.expired
        and credentials.refresh_token
    ):
        credentials.refresh(
            Request()
        )

        token_file.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

        return credentials

    # -----------------------------------------------------
    # TOKEN CAN NO LONGER BE USED
    # -----------------------------------------------------

    raise RuntimeError(
        f"OAuth token for {account} is no longer valid. "
        "Use login_gmail() to authenticate again."
    )


# ---------------------------------------------------------
# GET CURRENT GMAIL ACCOUNT
# ---------------------------------------------------------

def get_gmail_account() -> str:
    """Return the Gmail address currently authenticated."""

    credentials = authenticate_gmail()

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
    )

    profile = (
        service.users()
        .getProfile(
            userId="me"
        )
        .execute()
    )

    account = profile["emailAddress"]

    # Keep selected-account state synchronized.
    save_selected_account(
        account
    )

    return account


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

def login_gmail() -> str:
    """
    Perform Google OAuth login.

    The account selected during OAuth becomes the
    currently selected account.
    """

    credentials = authenticate_gmail(
        force_login=True
    )

    service = build(
        "gmail",
        "v1",
        credentials=credentials,
    )

    profile = (
        service.users()
        .getProfile(
            userId="me"
        )
        .execute()
    )

    account = profile["emailAddress"]

    save_selected_account(
        account
    )

    return account


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

def logout_gmail() -> None:
    """
    Log out the currently selected Gmail account.

    The account's token and database are NOT deleted.
    Only the selected-account state is cleared.
    """

    account = get_selected_account()

    if account:
        print(
            f"Logging out: {account}"
        )

    clear_selected_account()
