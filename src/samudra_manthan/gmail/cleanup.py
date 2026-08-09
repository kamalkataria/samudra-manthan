import time
from googleapiclient.errors import HttpError

from .client import get_gmail_service
from .labels import get_or_create_delete_label
from ..storage.database import get_connection, mark_messages_trashed


def find_messages(service, query: str) -> list[str]:
    message_ids = []
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, pageToken=page_token, maxResults=500)
            .execute()
        )
        message_ids.extend(message["id"] for message in response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return message_ids


def get_messages_with_label(service, label_id: str) -> set[str]:
    message_ids = set()
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(userId="me", labelIds=[label_id], pageToken=page_token, maxResults=500)
            .execute()
        )
        message_ids.update(message["id"] for message in response.get("messages", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return message_ids


def _get_label_id(service, label_name: str) -> str:
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    label_id = next((label["id"] for label in labels if label.get("name") == label_name), None)
    if label_id is None:
        raise ValueError(f"Gmail label not found: {label_name}")
    return label_id


def plan_delete(query: str, protected_label: str) -> tuple[list[str], set[str]]:
    service = get_gmail_service()
    candidates = find_messages(service, query)
    protected_label_id = _get_label_id(service, protected_label)
    protected = get_messages_with_label(service, protected_label_id)

    candidate_set = set(candidates)
    protected_matching = candidate_set & protected
    deletable = [msg_id for msg_id in candidates if msg_id not in protected]

    return deletable, protected_matching


def plan_delete_received(protected_label: str, account_email: str) -> tuple[list[str], set[str]]:
    """Calculate which RECEIVED messages would be moved to Trash."""
    service = get_gmail_service()
    print("Loading candidate inbox message IDs from local database...")

    connection = get_connection()
    rows = connection.execute(
        "SELECT id FROM messages WHERE trashed = 0 AND sender_email != ?", (account_email,)
    ).fetchall()
    connection.close()

    all_local_ids = {row["id"] for row in rows}
    protected_label_id = _get_label_id(service, protected_label)
    protected = get_messages_with_label(service, protected_label_id)

    deletable = sorted(all_local_ids - protected)
    return deletable, protected


# def plan_delete_sent(protected_label: str, account_email: str) -> tuple[list[str], set[str]]:
#     """Calculate which SENT messages would be moved to Trash."""
#     service = get_gmail_service()
#     print("Loading candidate sent message IDs from local database...")

#     connection = get_connection()
#     rows = connection.execute(
#         "SELECT id FROM messages WHERE trashed = 0 AND sender_email = ?", (account_email,)
#     ).fetchall()
#     connection.close()

#     all_local_ids = {row["id"] for row in rows}
#     protected_label_id = _get_label_id(service, protected_label)
#     protected = get_messages_with_label(service, protected_label_id)

#     deletable = sorted(all_local_ids - protected)
#     return deletable, protected


def plan_delete_sent(protected_label: str, account_email: str) -> tuple[list[str], set[str]]:
    """Calculate which SENT messages would be moved to Trash."""
    service = get_gmail_service()
    print("Loading candidate sent message IDs from local database...")

    connection = get_connection()
    
    # -------------------------------------------------------------
    # THE FIX: Only target sent messages that actually have a 
    # recipient email, matching exactly what Review Mode showed you.
    # -------------------------------------------------------------
    rows = connection.execute(
        """
        SELECT id FROM messages 
        WHERE trashed = 0 
          AND sender_email = ? 
          AND recipient_email IS NOT NULL 
          AND recipient_email != ''
        """, 
        (account_email,)
    ).fetchall()
    
    connection.close()

    all_local_ids = {row["id"] for row in rows}
    protected_label_id = _get_label_id(service, protected_label)
    protected = get_messages_with_label(service, protected_label_id)

    # Filter out anything protected
    deletable = sorted(all_local_ids - protected)
    return deletable, protected

def trash_messages(message_ids: list[str]) -> int:
    if not message_ids:
        return 0

    service = get_gmail_service()
    delete_label_id = get_or_create_delete_label()

    batch_size = 1000
    total = len(message_ids)

    for start in range(0, total, batch_size):
        batch = message_ids[start:start + batch_size]

        for attempt in range(1, 4):
            try:
                (
                    service.users()
                    .messages()
                    .batchModify(
                        userId="me",
                        body={"ids": batch, "addLabelIds": ["TRASH", delete_label_id]},
                    )
                    .execute()
                )
                break
            except HttpError as exc:
                if exc.resp.status in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(2 ** attempt)
                else:
                    raise exc

        mark_messages_trashed(batch)
        completed = min(start + batch_size, total)
        print(f"\rMoved to Trash + SamudraManthan: {completed:,}/{total:,}", end="", flush=True)

    print()
    return total


def empty_gmail_trash() -> int:
    service = get_gmail_service()
    print("\nLocating messages in Trash...")
    trashed_ids = find_messages(service, "in:trash")
    
    if not trashed_ids:
        print("Trash is already empty.")
        return 0

    total = len(trashed_ids)
    print(f"Permanently deleting {total:,} trashed messages...")
    
    batch_size = 1000
    for start in range(0, total, batch_size):
        batch = trashed_ids[start : start + batch_size]
        
        for attempt in range(1, 4):
            try:
                service.users().messages().batchDelete(
                    userId="me",
                    body={"ids": batch}
                ).execute()
                break
            except HttpError as exc:
                if exc.resp.status in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(2 ** attempt)
                else:
                    raise exc

        completed = min(start + batch_size, total)
        print(f"\rPermanently Deleted: {completed:,}/{total:,}", end="", flush=True)

    print("\nTrash emptied successfully!")
    return total