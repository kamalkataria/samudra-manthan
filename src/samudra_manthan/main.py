from pathlib import Path

from samudra_manthan.gmail.auth import (
    get_gmail_account,
    login_gmail,
    logout_gmail,
)
from samudra_manthan.gmail.cleanup import (
    plan_delete_received,
    plan_delete_sent,
    trash_messages,
    empty_gmail_trash,
)
from samudra_manthan.gmail.messages import scan_mailbox
from samudra_manthan.review import review_mode, review_sent_mode


# ---------------------------------------------------------
# PROJECT / ACCOUNT PATHS
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACCOUNTS_DIR = PROJECT_ROOT / "data" / "accounts"


def get_logged_in_account() -> str | None:
    try:
        return get_gmail_account()
    except Exception:
        return None


def get_account_directory() -> Path:
    account = get_gmail_account()
    safe_account = (
        account.strip().lower()
        .replace("@", "_").replace("/", "_")
        .replace("\\", "_").replace(":", "_")
    )
    account_dir = ACCOUNTS_DIR / safe_account
    account_dir.mkdir(parents=True, exist_ok=True)
    return account_dir


def get_session_file() -> Path:
    return get_account_directory() / ".samudra_manthan_session"


def save_session_label(label_name: str) -> None:
    session_file = get_session_file()
    session_file.write_text(label_name.strip() + "\n", encoding="utf-8")


def load_session_label() -> str | None:
    session_file = get_session_file()
    if not session_file.exists():
        return None
    label = session_file.read_text(encoding="utf-8").strip()
    return label or None


# ---------------------------------------------------------
# MODES
# ---------------------------------------------------------

def scan_mode() -> None:
    print("\n" + "=" * 60)
    print("SAMUDRA MANTHAN — SCAN / REFRESH")
    print("=" * 60 + "\n")

    account = get_logged_in_account()
    if not account:
        print("No Gmail account is currently connected.\nLogin first.\n")
        return

    print(f"Scanning account:\n  {account}\n")
    print(f"Account data directory:\n  {get_account_directory()}\n")
    print("Refreshing local Gmail index...\n")

    try:
        scan_mailbox()
    except Exception as exc:
        print(f"\nScan failed: {exc}\n")
        return

    print("\n" + "=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60 + "\n")
    print(f"Account: {account}")
    print(f"Database: {get_account_directory()}\n")


def login_mode() -> None:
    print("\n" + "=" * 60)
    print("SAMUDRA MANTHAN — GOOGLE LOGIN")
    print("=" * 60 + "\n")
    print("Opening Google authentication...\n")

    try:
        account = login_gmail()
    except Exception as exc:
        print(f"\nGoogle login failed: {exc}\n")
        return

    print("\n" + "=" * 60)
    print("LOGIN SUCCESSFUL")
    print("=" * 60 + "\n")
    print(f"Connected Gmail account:\n  {account}\n")
    print(f"Account data directory:\n  {get_account_directory()}\n")


def logout_mode() -> None:
    print("\n" + "=" * 60)
    print("SAMUDRA MANTHAN — LOGOUT")
    print("=" * 60 + "\n")

    account = get_logged_in_account()
    if not account:
        print("No Gmail account is currently connected.\n")
        return

    print(f"Current account:\n  {account}\n")
    confirmation = input("Logout this account? [y/N] > ").strip().lower()

    if confirmation not in ("y", "yes"):
        print("\nLogout cancelled.\n")
        return

    logout_gmail()
    print("\nLogged out successfully.\n")


def review_and_save(mode="received") -> None:
    account = get_logged_in_account()
    if not account:
        print("\nNo Gmail account connected.\nLogin first.\n")
        return

    print(f"\nReviewing account:\n  {account}\n")
    print(f"Account data directory:\n  {get_account_directory()}\n")

    if mode == "sent":
        label_name = review_sent_mode()
    else:
        label_name = review_mode()

    if label_name:
        save_session_label(label_name)
        print(f"\nActive session saved: {label_name}")
        print("Delete Mode will use this session for this account only.\n")


def delete_mode(mode="received") -> None:
    print("\n" + "=" * 60)
    print(f"SAMUDRA MANTHAN — DELETE MODE ({mode.upper()})")
    print("=" * 60 + "\n")

    account = get_logged_in_account()
    if not account:
        print("No Gmail account connected.\nLogin first.\n")
        return

    print(f"Connected Gmail account:\n  {account}\n")
    print(f"Account database:\n  {get_account_directory()}\n")

    protected_label = load_session_label()
    if not protected_label:
        print("No active protection session found for this account.\n\nRun Review & Protect first.\n")
        return

    print(f"Current protection label:\n  {protected_label}\n")
    print("Scanning mailbox...\n")

    try:
        if mode == "sent":
            deletable, protected = plan_delete_sent(protected_label, account)
        else:
            deletable, protected = plan_delete_received(protected_label, account)
    except Exception as exc:
        print(f"\nDelete planning failed: {exc}\n")
        return

    total = len(deletable) + len(protected)

    print("=" * 60)
    print("DELETE PREVIEW")
    print("=" * 60 + "\n")
    print(f"Total messages:     {total:,}")
    print(f"Protected:          {len(protected):,}")
    print(f"Will move to Trash: {len(deletable):,}\n")

    if not deletable:
        print("Nothing will be moved to Trash.\n")
        return

    print("Only messages carrying the current protection label are excluded.\n")
    confirmation = input("Move ALL unprotected messages to Trash? [y/N] > ").strip().lower()

    if confirmation not in ("y", "yes"):
        print("\nDelete cancelled.\n")
        return

    print("\nMoving messages to Trash...\n")

    try:
        moved = trash_messages(deletable)
    except Exception as exc:
        print(f"\nTrash operation failed: {exc}\n")
        return

    print("\n" + "=" * 60)
    print("DELETE COMPLETE")
    print("=" * 60 + "\n")
    print(f"Moved to Trash: {moved:,}")
    print(f"Protected:      {len(protected):,}\n")


# ---------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------

def main() -> None:
    while True:
        account = get_logged_in_account()

        print("\n" + "=" * 60)
        print("SAMUDRA MANTHAN")
        print("=" * 60)
        print("The open-source Gmail cleanup utility")
        print("Version: 0.1.0")
        print("=" * 60 + "\n")

        if account:
            print(f"Connected Gmail account:\n  {account}\n")
            print(f"Account data directory:\n  {get_account_directory()}\n")

            current_label = load_session_label()
            if current_label:
                print(f"Active protection session:\n  {current_label}\n")
            else:
                print("No active protection session for this account.\n")

            print("1. Scan / Refresh Gmail")
            print("2. Review & Protect (Inbox)")
            print("3. Delete Unprotected (Inbox)")
            print("4. Review & Protect (Sentbox)")
            print("5. Delete Unprotected (Sentbox)")
            print("6. Empty Trash (Permanent)")
            print("7. Logout")
            print("8. Exit\n")

            choice = input("Select > ").strip().lower()

            if choice == "1":
                scan_mode()
            elif choice == "2":
                review_and_save(mode="received")
            elif choice == "3":
                delete_mode(mode="received")
            elif choice == "4":
                review_and_save(mode="sent")
            elif choice == "5":
                delete_mode(mode="sent")
            elif choice == "6":
                print("\n" + "=" * 60)
                print("EMPTY TRASH")
                print("=" * 60 + "\n")
                confirm = input(
                    "PERMANENTLY delete everything in Trash? This cannot be undone. [y/N] > "
                ).strip().lower()
                if confirm in ("y", "yes"):
                    empty_gmail_trash()
            elif choice == "7":
                logout_mode()
            elif choice in ("8", "q", "quit", "exit"):
                print("\nGoodbye.")
                return
            else:
                print("\nInvalid choice.")

        else:
            print("No Gmail account connected.\n")
            print("1. Login with Google")
            print("2. Exit\n")

            choice = input("Select > ").strip().lower()

            if choice == "1":
                login_mode()
            elif choice in ("2", "q", "quit", "exit"):
                print("\nGoodbye.")
                return
            else:
                print("\nInvalid choice.")

if __name__ == "__main__":
    main()