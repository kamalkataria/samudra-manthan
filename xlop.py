from googleapiclient.errors import HttpError

from samudra_manthan.gmail.client import get_gmail_service


TARGET_LABEL = "NEVERDELETE"

# Gmail's built-in/system labels.
SYSTEM_LABELS = {
    "INBOX",
    "SENT",
    "TRASH",
    "SPAM",
    "DRAFT",
    "STARRED",
    "IMPORTANT",
    "UNREAD",
    "CATEGORY_PERSONAL",
    "CATEGORY_SOCIAL",
    "CATEGORY_PROMOTIONS",
    "CATEGORY_UPDATES",
    "CATEGORY_FORUMS",
}


def get_labels(service):
    response = (
        service.users()
        .labels()
        .list(userId="me")
        .execute()
    )

    return response.get("labels", [])


def get_or_create_neverdelete(service):
    labels = get_labels(service)

    for label in labels:
        if label["name"] == TARGET_LABEL:
            return label["id"]

    print(f"Creating Gmail label: {TARGET_LABEL}")

    label = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": TARGET_LABEL,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )

    return label["id"]


def get_custom_label_ids(service, neverdelete_id):
    labels = get_labels(service)

    custom = []

    print()
    print("Labels that will be protected:")
    print("-" * 60)

    for label in labels:
        label_id = label["id"]
        name = label["name"]

        if label_id == neverdelete_id:
            continue

        if name in SYSTEM_LABELS:
            continue

        custom.append(label_id)

        print(f"  {name}")

    print("-" * 60)
    print(f"Custom labels: {len(custom):,}")

    return custom


def get_message_ids_for_labels(service, label_ids):
    message_ids = set()

    for label_id in label_ids:
        print(f"Reading messages for label: {label_id}")

        page_token = None

        while True:
            response = (
                service.users()
                .messages()
                .list(
                    userId="me",
                    labelIds=[label_id],
                    maxResults=500,
                    pageToken=page_token,
                )
                .execute()
            )

            for message in response.get("messages", []):
                message_ids.add(message["id"])

            page_token = response.get("nextPageToken")

            if not page_token:
                break

    return list(message_ids)


def apply_neverdelete(service, message_ids, label_id):
    total = len(message_ids)

    if total == 0:
        return

    batch_size = 1000

    for start in range(0, total, batch_size):
        batch = message_ids[start:start + batch_size]

        (
            service.users()
            .messages()
            .batchModify(
                userId="me",
                body={
                    "ids": batch,
                    "addLabelIds": [label_id],
                },
            )
            .execute()
        )

        completed = min(
            start + len(batch),
            total,
        )

        print(
            f"Protected: "
            f"{completed:,}/{total:,}"
        )


def main():
    print()
    print("=" * 70)
    print("SAMUDRA MANTHAN — PROTECT LABELED MAIL")
    print("=" * 70)
    print()

    service = get_gmail_service()

    neverdelete_id = get_or_create_neverdelete(service)

    custom_labels = get_custom_label_ids(
        service,
        neverdelete_id,
    )

    if not custom_labels:
        print()
        print("No custom labels found.")
        return

    print()
    print("Collecting messages...")
    print()

    message_ids = get_message_ids_for_labels(
        service,
        custom_labels,
    )

    print()
    print(
        f"Unique messages found: "
        f"{len(message_ids):,}"
    )

    if not message_ids:
        print("Nothing to protect.")
        return

    print()
    print(
        "The following operation will ONLY add:"
    )
    print()
    print(f"    {TARGET_LABEL}")
    print()
    print("No existing labels will be removed.")
    print("No messages will be deleted.")
    print()

    confirmation = input(
        "Continue? [y/N] > "
    ).strip().lower()

    if confirmation not in ("y", "yes"):
        print()
        print("Cancelled.")
        return

    print()
    print("Applying NEVERDELETE...")
    print()

    try:
        apply_neverdelete(
            service,
            message_ids,
            neverdelete_id,
        )

    except HttpError as exc:
        print()
        print(f"Gmail API error: {exc}")
        return

    print()
    print("=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print()
    print(
        f"Messages protected: "
        f"{len(message_ids):,}"
    )
    print()
    print(
        f"Protection label: {TARGET_LABEL}"
    )
    print()


if __name__ == "__main__":
    main()
