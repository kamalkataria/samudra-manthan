from .client import get_gmail_service
from .labels import get_or_create_delete_label
from ..storage.database import mark_messages_trashed

def find_messages(service, query: str) -> list[str]:
    """Return all Gmail message IDs matching a Gmail search query."""

    message_ids = []
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                pageToken=page_token,
                maxResults=500,
            )
            .execute()
        )

        message_ids.extend(
            message["id"]
            for message in response.get("messages", [])
        )

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return message_ids


def get_messages_with_label(
    service,
    label_id: str,
) -> set[str]:
    """Return all Gmail message IDs carrying the specified label."""

    message_ids = set()
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=[label_id],
                pageToken=page_token,
                maxResults=500,
            )
            .execute()
        )

        message_ids.update(
            message["id"]
            for message in response.get("messages", [])
        )

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return message_ids


def _get_label_id(
    service,
    label_name: str,
) -> str:
    """Return the Gmail label ID for a label name."""

    labels = (
        service.users()
        .labels()
        .list(userId="me")
        .execute()
        .get("labels", [])
    )

    label_id = next(
        (
            label["id"]
            for label in labels
            if label.get("name") == label_name
        ),
        None,
    )

    if label_id is None:
        raise ValueError(
            f"Gmail label not found: {label_name}"
        )

    return label_id


def plan_delete(
    query: str,
    protected_label: str,
) -> tuple[list[str], set[str]]:
    """
    Calculate which messages matching a Gmail query would be
    moved to Trash.

    Messages carrying the protection label are excluded.

    Nothing is modified or deleted.
    """

    service = get_gmail_service()

    candidates = find_messages(
        service,
        query,
    )

    protected_label_id = _get_label_id(
        service,
        protected_label,
    )

    protected = get_messages_with_label(
        service,
        protected_label_id,
    )

    candidate_set = set(candidates)

    protected_matching = (
        candidate_set & protected
    )

    deletable = [
        message_id
        for message_id in candidates
        if message_id not in protected
    ]

    return deletable, protected_matching


def plan_delete_all(
    protected_label: str,
) -> tuple[list[str], set[str]]:
    """
    Calculate which messages would be moved to Trash.

    Every Gmail message is a candidate except messages carrying
    the specified protection label.

    Nothing is modified or deleted.
    """

    service = get_gmail_service()

    print("Loading all Gmail message IDs...")

    all_messages = set(
        find_messages(
            service,
            "",
        )
    )

    protected_label_id = _get_label_id(
        service,
        protected_label,
    )

    protected = get_messages_with_label(
        service,
        protected_label_id,
    )

    deletable = sorted(
        all_messages - protected
    )

    return deletable, protected


def trash_messages(
    message_ids: list[str],
) -> int:
    """
    Move messages to Gmail Trash and apply the SamudraManthan
    audit label in the same Gmail API operation.

    Returns the number of messages submitted to Trash.
    """

    if not message_ids:
        return 0

    service = get_gmail_service()

    delete_label_id = (
        get_or_create_delete_label()
    )

    batch_size = 1000
    total = len(message_ids)

    for start in range(
        0,
        total,
        batch_size,
    ):
        batch = message_ids[
            start:start + batch_size
        ]

        (
            service.users()
            .messages()
            .batchModify(
                userId="me",
                body={
                    "ids": batch,
                    "addLabelIds": [
                        "TRASH",
                        delete_label_id,
                    ],
                },
            )
            .execute()
        )
        mark_messages_trashed(batch)
        

        completed = min(
            start + batch_size,
            total,
        )

        print(
            f"\rMoved to Trash + "
            f"SamudraManthan: "
            f"{completed:,}/{total:,}",
            end="",
            flush=True,
        )

    print()

    return total