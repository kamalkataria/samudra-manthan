from pathlib import Path

from samudra_manthan.gmail.auth import (
    get_gmail_account,
    login_gmail,
    logout_gmail,
)
from samudra_manthan.gmail.cleanup import (
    plan_delete_all,
    trash_messages,
)
from samudra_manthan.gmail.messages import scan_mailbox
from samudra_manthan.review import review_mode


# ---------------------------------------------------------
# PROJECT / ACCOUNT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ACCOUNTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "accounts"
)


# ---------------------------------------------------------
# ACCOUNT
# ---------------------------------------------------------

def get_logged_in_account() -> str | None:
    """Return the currently authenticated Gmail account."""

    try:
        return get_gmail_account()

    except Exception:
        return None


def get_account_directory() -> Path:
    """Return the data directory for the current Gmail account."""

    account = get_gmail_account()

    safe_account = (
        account
        .strip()
        .lower()
        .replace("@", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )

    account_dir = (
        ACCOUNTS_DIR
        / safe_account
    )

    account_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return account_dir


# ---------------------------------------------------------
# ACCOUNT-SPECIFIC SESSION
# ---------------------------------------------------------

def get_session_file() -> Path:
    """Return the protection-session file for the current account."""

    return (
        get_account_directory()
        / ".samudra_manthan_session"
    )


def save_session_label(
    label_name: str,
) -> None:
    """Save the current protection session for this account."""

    session_file = get_session_file()

    session_file.write_text(
        label_name.strip() + "\n",
        encoding="utf-8",
    )


def load_session_label() -> str | None:
    """Load the protection session for this account."""

    session_file = get_session_file()

    if not session_file.exists():
        return None

    label = (
        session_file
        .read_text(
            encoding="utf-8",
        )
        .strip()
    )

    return label or None


# ---------------------------------------------------------
# SCAN / REFRESH
# ---------------------------------------------------------

def scan_mode() -> None:
    """Scan the current Gmail account into its SQLite database."""

    print()
    print("=" * 60)
    print("SAMUDRA MANTHAN — SCAN / REFRESH")
    print("=" * 60)
    print()

    account = get_logged_in_account()

    if not account:
        print(
            "No Gmail account is currently connected."
        )
        print(
            "Login first."
        )
        print()
        return

    print(
        "Scanning account:"
    )
    print(
        f"  {account}"
    )
    print()

    print(
        "Account data directory:"
    )
    print(
        f"  {get_account_directory()}"
    )
    print()

    print(
        "Refreshing local Gmail index..."
    )
    print()

    try:
        scan_mailbox()

    except Exception as exc:
        print()
        print(
            f"Scan failed: {exc}"
        )
        print()
        return

    print()
    print("=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print()

    print(
        f"Account: {account}"
    )

    print(
        f"Database: {get_account_directory()}"
    )

    print()


# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------

def login_mode() -> None:
    """Open Google OAuth login and display the connected account."""

    print()
    print("=" * 60)
    print("SAMUDRA MANTHAN — GOOGLE LOGIN")
    print("=" * 60)
    print()

    print(
        "Opening Google authentication..."
    )
    print()

    try:
        account = login_gmail()

    except Exception as exc:
        print()
        print(
            f"Google login failed: {exc}"
        )
        print()
        return

    print()
    print("=" * 60)
    print("LOGIN SUCCESSFUL")
    print("=" * 60)
    print()

    print(
        "Connected Gmail account:"
    )
    print(
        f"  {account}"
    )

    print()

    print(
        "Account data directory:"
    )
    print(
        f"  {get_account_directory()}"
    )

    print()


# ---------------------------------------------------------
# LOGOUT
# ---------------------------------------------------------

def logout_mode() -> None:
    """Log out the currently connected Gmail account."""

    print()
    print("=" * 60)
    print("SAMUDRA MANTHAN — LOGOUT")
    print("=" * 60)
    print()

    account = get_logged_in_account()

    if not account:
        print(
            "No Gmail account is currently connected."
        )
        print()
        return

    print(
        "Current account:"
    )
    print(
        f"  {account}"
    )
    print()

    confirmation = input(
        "Logout this account? [y/N] > "
    ).strip().lower()

    if confirmation not in (
        "y",
        "yes",
    ):
        print()
        print(
            "Logout cancelled."
        )
        print()
        return

    logout_gmail()

    print()
    print(
        "Logged out successfully."
    )
    print()


# ---------------------------------------------------------
# DELETE MODE
# ---------------------------------------------------------

def delete_mode() -> None:
    """
    Preview and optionally move all unprotected messages
    for the current Gmail account to Trash.
    """

    print()
    print("=" * 60)
    print("SAMUDRA MANTHAN — DELETE MODE")
    print("=" * 60)
    print()

    account = get_logged_in_account()

    if not account:
        print(
            "No Gmail account connected."
        )
        print(
            "Login first."
        )
        print()
        return

    print(
        "Connected Gmail account:"
    )
    print(
        f"  {account}"
    )
    print()

    print(
        "Account database:"
    )
    print(
        f"  {get_account_directory()}"
    )
    print()

    protected_label = load_session_label()

    if not protected_label:
        print(
            "No active protection session found "
            "for this account."
        )
        print()
        print(
            "Run Review & Protect first."
        )
        print()
        return

    print(
        "Current protection label:"
    )
    print(
        f"  {protected_label}"
    )
    print()

    print(
        "Scanning mailbox..."
    )
    print()

    try:
        deletable, protected = (
            plan_delete_all(
                protected_label
            )
        )

    except Exception as exc:
        print()
        print(
            f"Delete planning failed: {exc}"
        )
        print()
        return

    total = (
        len(deletable)
        + len(protected)
    )

    print("=" * 60)
    print("DELETE PREVIEW")
    print("=" * 60)
    print()

    print(
        f"Total messages:     {total:,}"
    )

    print(
        f"Protected:          {len(protected):,}"
    )

    print(
        f"Will move to Trash: {len(deletable):,}"
    )

    print()

    if not deletable:
        print(
            "Nothing will be moved to Trash."
        )
        print()
        return

    print(
        "Only messages carrying the current "
        "protection label are excluded."
    )
    print()

    confirmation = input(
        "Move ALL unprotected messages to Trash? [y/N] > "
    ).strip().lower()

    if confirmation not in (
        "y",
        "yes",
    ):
        print()
        print(
            "Delete cancelled."
        )
        print()
        return

    print()
    print(
        "Moving messages to Trash..."
    )
    print()

    try:
        moved = trash_messages(
            deletable
        )

    except Exception as exc:
        print()
        print(
            f"Trash operation failed: {exc}"
        )
        print()
        return

    print()
    print("=" * 60)
    print("DELETE COMPLETE")
    print("=" * 60)
    print()

    print(
        f"Moved to Trash: {moved:,}"
    )

    print(
        f"Protected:      {len(protected):,}"
    )

    print()


# ---------------------------------------------------------
# REVIEW & PROTECT
# ---------------------------------------------------------

def review_and_save() -> None:
    """Run Review Mode and save its session label for this account."""

    account = get_logged_in_account()

    if not account:
        print()
        print(
            "No Gmail account connected."
        )
        print(
            "Login first."
        )
        print()
        return

    print()
    print(
        "Reviewing account:"
    )
    print(
        f"  {account}"
    )
    print()

    print(
        "Account data directory:"
    )
    print(
        f"  {get_account_directory()}"
    )
    print()

    label_name = review_mode()

    if label_name:
        save_session_label(
            label_name
        )

        print()
        print(
            f"Active session saved: {label_name}"
        )

        print(
            "Delete Mode will use this "
            "session for this account only."
        )

        print()


# ---------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------

def main() -> None:
    """Main Samudra Manthan application."""

    while True:

        account = (
            get_logged_in_account()
        )

        print()
        print("=" * 60)
        print("SAMUDRA MANTHAN")
        print("=" * 60)
        print(
            "The open-source Gmail cleanup utility"
        )
        print(
            "Version: 0.1.0"
        )
        print("=" * 60)
        print()

        # -------------------------------------------------
        # LOGGED IN
        # -------------------------------------------------

        if account:

            print(
                "Connected Gmail account:"
            )
            print(
                f"  {account}"
            )
            print()

            print(
                "Account data directory:"
            )
            print(
                f"  {get_account_directory()}"
            )
            print()

            current_label = (
                load_session_label()
            )

            if current_label:

                print(
                    "Active protection session:"
                )
                print(
                    f"  {current_label}"
                )
                print()

            else:

                print(
                    "No active protection session "
                    "for this account."
                )
                print()

            print(
                "1. Scan / Refresh Gmail"
            )

            print(
                "2. Review & Protect"
            )

            print(
                "3. Delete"
            )

            print(
                "4. Logout"
            )

            print(
                "5. Exit"
            )

            print()

            choice = input(
                "Select > "
            ).strip().lower()

            if choice == "1":

                scan_mode()

            elif choice == "2":

                review_and_save()

            elif choice == "3":

                delete_mode()

            elif choice == "4":

                logout_mode()

            elif choice in (
                "5",
                "q",
                "quit",
                "exit",
            ):

                print()
                print(
                    "Goodbye."
                )
                return

            else:

                print()
                print(
                    "Invalid choice."
                )

        # -------------------------------------------------
        # LOGGED OUT
        # -------------------------------------------------

        else:

            print(
                "No Gmail account connected."
            )
            print()

            print(
                "1. Login with Google"
            )

            print(
                "2. Exit"
            )

            print()

            choice = input(
                "Select > "
            ).strip().lower()

            if choice == "1":

                login_mode()

            elif choice in (
                "2",
                "q",
                "quit",
                "exit",
            ):

                print()
                print(
                    "Goodbye."
                )
                return

            else:

                print()
                print(
                    "Invalid choice."
                )


if __name__ == "__main__":
    main()
