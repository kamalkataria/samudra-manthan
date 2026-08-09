from samudra_manthan.gmail.client import get_gmail_service


LABEL_NAME = "samudramanthansaved"
BATCH_SIZE = 20


def get_or_create_label(service):
    response = (
        service.users()
        .labels()
        .list(userId="me")
        .execute()
    )

    for label in response.get("labels", []):
        if label["name"] == LABEL_NAME:
            return label["id"]

    print(f"Creating Gmail label: {LABEL_NAME}")

    label = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": LABEL_NAME,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )

    return label["id"]


def get_all_inbox_message_ids(service):
    message_ids = []
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=500,
                pageToken=page_token,
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


def move_messages(service, message_ids, label_id):
    total = len(message_ids)

    for start in range(0, total, BATCH_SIZE):
        batch = message_ids[
            start:start + BATCH_SIZE
        ]

        (
            service.users()
            .messages()
            .batchModify(
                userId="me",
                body={
                    "ids": batch,
                    "addLabelIds": [label_id],
                    "removeLabelIds": ["INBOX"],
                },
            )
            .execute()
        )

        completed = min(
            start + len(batch),
            total,
        )

        print(
            f"Moved: {completed:,}/{total:,}",
            end="\r",
            flush=True,
        )

    print()


def main():
    print()
    print("=" * 60)
    print("SAMUDRA MANTHAN — SAVE REMAINING INBOX")
    print("=" * 60)
    print()

    service = get_gmail_service()

    print("Finding/creating Gmail label...")
    label_id = get_or_create_label(service)

    print("Finding Inbox messages...")
    message_ids = get_all_inbox_message_ids(service)

    print()
    print(f"Inbox messages found: {len(message_ids):,}")
    print()

    if not message_ids:
        print("No Inbox messages found.")
        return

    confirmation = input(
        f"Move these {len(message_ids):,} messages "
        f"to '{LABEL_NAME}'? [y/N] > "
    ).strip().lower()

    if confirmation not in ("y", "yes"):
        print()
        print("Cancelled. No messages were changed.")
        return

    print()
    print("Moving messages...")
    move_messages(
        service,
        message_ids,
        label_id,
    )

    print()
    print("=" * 60)
    print("COMPLETE")
    print("=" * 60)
    print()
    print(f"Moved: {len(message_ids):,}")
    print(f"Label: {LABEL_NAME}")
    print("Inbox label removed.")
    print("Messages were NOT deleted.")
    print()


if __name__ == "__main__":
    main()
