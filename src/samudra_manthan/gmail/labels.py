from datetime import datetime, timezone

from .client import get_gmail_service


def get_or_create_label(name: str) -> str:
    """Return the Gmail label ID, creating it if necessary."""

    service = get_gmail_service()

    response = (
        service.users()
        .labels()
        .list(userId="me")
        .execute()
    )

    for label in response.get("labels", []):
        if label.get("name") == name:
            return label["id"]

    label = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )

    return label["id"]


def create_session_label() -> tuple[str, str]:
    """
    Create a unique protection label for this app run.

    Returns:
        (label_name, label_id)
    """

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    label_name = f"SM_KEEP_{timestamp}"

    label_id = get_or_create_label(label_name)

    return label_name, label_id


def apply_label(message_id: str, label_id: str) -> None:
    """Apply a Gmail label to one message."""

    service = get_gmail_service()

    (
        service.users()
        .messages()
        .modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [label_id]},
        )
        .execute()
    )

def get_or_create_delete_label() -> str:
    """Return the label ID used for messages moved by Samudra Manthan."""

    return get_or_create_label("SamudraManthan")