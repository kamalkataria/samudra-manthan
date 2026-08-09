import re
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"
ACCOUNTS_DIR = DATA_DIR / "accounts"


def _safe_account_name(account: str) -> str:
    """
    Convert a Gmail address into a safe directory name.
    """

    account = account.strip().lower()

    if not account:
        raise ValueError(
            "Gmail account cannot be empty."
        )

    return re.sub(
        r"[^a-zA-Z0-9._-]",
        "_",
        account,
    )


def get_current_gmail_account() -> str:
    """
    Return the Gmail account currently authenticated.

    The import is intentionally inside the function to avoid
    circular imports during application startup.
    """

    from samudra_manthan.gmail.auth import (
        get_gmail_account,
    )

    account = get_gmail_account()

    if not account:
        raise RuntimeError(
            "No Gmail account is currently authenticated."
        )

    return account


def get_database_path() -> Path:
    """
    Return the SQLite database path for the currently
    authenticated Gmail account.
    """

    account = get_current_gmail_account()

    safe_account = _safe_account_name(
        account
    )

    account_dir = (
        ACCOUNTS_DIR / safe_account
    )

    account_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        account_dir
        / "samudra_manthan.db"
    )


def get_connection():
    """
    Return a SQLite connection for the currently
    authenticated Gmail account.
    """

    database_path = get_database_path()

    connection = sqlite3.connect(
        database_path
    )

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """
    Create the database tables and indexes.
    """

    connection = get_connection()

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            thread_id TEXT,
            sender_email TEXT NOT NULL,
            sender_name TEXT,
            subject TEXT,
            date TEXT,
            labels TEXT,
            trashed INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS senders (
            email TEXT PRIMARY KEY,
            message_count INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_messages_sender
        ON messages(sender_email);

        CREATE INDEX IF NOT EXISTS idx_messages_date
        ON messages(date);
        """
    )

    # ---------------------------------------------------------
    # MIGRATION FOR OLD DATABASES
    # ---------------------------------------------------------

    columns = {
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(messages)"
        ).fetchall()
    }

    if "trashed" not in columns:
        connection.execute(
            """
            ALTER TABLE messages
            ADD COLUMN trashed INTEGER NOT NULL DEFAULT 0
            """
        )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_trashed
        ON messages(trashed)
        """
    )

    connection.commit()
    connection.close()


def save_messages(messages):
    """
    Save scanned Gmail messages to the local database.

    Existing trashed state is preserved when a message
    is rescanned.
    """

    if not messages:
        return

    connection = get_connection()

    message_ids = [
        message["id"]
        for message in messages
    ]

    placeholders = ",".join(
        "?" for _ in message_ids
    )

    existing_rows = connection.execute(
        f"""
        SELECT id, trashed
        FROM messages
        WHERE id IN ({placeholders})
        """,
        message_ids,
    ).fetchall()

    existing_trashed = {
        row["id"]: row["trashed"]
        for row in existing_rows
    }

    connection.executemany(
        """
        INSERT OR REPLACE INTO messages (
            id,
            thread_id,
            sender_email,
            sender_name,
            subject,
            date,
            labels,
            trashed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                message["id"],
                message.get(
                    "thread_id"
                ),
                message.get(
                    "sender_email",
                    "",
                ),
                message.get(
                    "sender_name",
                    "",
                ),
                message.get(
                    "subject",
                    "",
                ),
                message.get(
                    "date",
                    "",
                ),
                ",".join(
                    message.get(
                        "labels",
                        [],
                    )
                ),
                existing_trashed.get(
                    message["id"],
                    0,
                ),
            )
            for message in messages
        ],
    )

    connection.commit()
    connection.close()


def mark_messages_trashed(
    message_ids,
):
    """
    Mark successfully trashed Gmail messages
    in the current user's local database.
    """

    if not message_ids:
        return

    connection = get_connection()

    connection.executemany(
        """
        UPDATE messages
        SET trashed = 1
        WHERE id = ?
        """,
        [
            (message_id,)
            for message_id in message_ids
        ],
    )

    connection.commit()
    connection.close()


def rebuild_sender_counts():
    """
    Rebuild sender statistics from active messages only.
    """

    connection = get_connection()

    connection.execute(
        """
        DELETE FROM senders
        """
    )

    connection.execute(
        """
        INSERT INTO senders (
            email,
            message_count
        )
        SELECT
            sender_email,
            COUNT(*)
        FROM messages
        WHERE sender_email != ''
          AND trashed = 0
        GROUP BY sender_email
        """
    )

    connection.commit()
    connection.close()