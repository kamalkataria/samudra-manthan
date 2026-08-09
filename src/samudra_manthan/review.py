from samudra_manthan.gmail.client import get_gmail_service
from samudra_manthan.gmail.labels import create_session_label
from samudra_manthan.storage.database import get_connection


# Keep this at 20 because your Gmail API setup is accepting it properly.
LABEL_BATCH_SIZE = 20


def get_sender_groups():
    """Load active sender groups from the local SQLite database.

    Trashed messages are excluded.

    No Gmail API calls are made while building the group list.
    """

    connection = get_connection()

    rows = connection.execute(
        """
        SELECT
            sender_email,
            COUNT(*) AS message_count
        FROM messages
        WHERE sender_email IS NOT NULL
          AND sender_email != ''
          AND trashed = 0
        GROUP BY sender_email
        ORDER BY message_count DESC, sender_email ASC
        """
    ).fetchall()

    connection.close()

    return [
        {
            "sender": row["sender_email"],
            "count": row["message_count"],
        }
        for row in rows
    ]


def get_message_ids_for_senders(senders):
    """Return active message IDs belonging to selected senders."""

    if not senders:
        return []

    connection = get_connection()

    placeholders = ",".join(
        "?" for _ in senders
    )

    rows = connection.execute(
        f"""
        SELECT id
        FROM messages
        WHERE sender_email IN ({placeholders})
          AND trashed = 0
        """,
        list(senders),
    ).fetchall()

    connection.close()

    return [
        row["id"]
        for row in rows
    ]


def display_groups(groups):
    """Display all active sender groups in one screen."""

    print()
    print("=" * 78)
    print("SAMUDRA MANTHAN — SENDER GROUPS")
    print("=" * 78)

    total_messages = sum(
        group["count"]
        for group in groups
    )

    print()
    print(
        f"Messages: {total_messages:,}   "
        f"Senders: {len(groups):,}"
    )
    print()

    print(
        f"{'#':>4}  {'MESSAGES':>8}  SENDER"
    )
    print("-" * 78)

    for number, group in enumerate(
        groups,
        start=1,
    ):
        print(
            f"{number:>4}  "
            f"{group['count']:>8,}  "
            f"{group['sender']}"
        )

    print("-" * 78)


def parse_selection(value, total):
    """Parse comma-separated sender numbers and ranges.

    Examples:
        1,2,3
        1-5
        1,4-7,12
    """

    selected = set()

    parts = [
        part.strip()
        for part in value.split(",")
        if part.strip()
    ]

    for part in parts:
        if "-" in part:
            pieces = part.split("-", 1)

            if len(pieces) != 2:
                raise ValueError(
                    f"Invalid range: {part}"
                )

            try:
                start = int(pieces[0])
                end = int(pieces[1])
            except ValueError:
                raise ValueError(
                    f"Invalid range: {part}"
                )

            if start > end:
                start, end = end, start

            if start < 1 or end > total:
                raise ValueError(
                    f"Range {part} is outside 1-{total}"
                )

            selected.update(
                range(start, end + 1)
            )

        else:
            try:
                number = int(part)
            except ValueError:
                raise ValueError(
                    f"Invalid group number: {part}"
                )

            if number < 1 or number > total:
                raise ValueError(
                    f"Number {number} is outside 1-{total}"
                )

            selected.add(number)

    return sorted(selected)


def display_selection(
    groups,
    selected_numbers,
):
    """Display selected sender groups."""

    print()
    print("=" * 78)
    print("SELECTED GROUPS")
    print("=" * 78)

    total_messages = 0

    for number in selected_numbers:
        group = groups[number - 1]

        print(
            f"{number:>4}  "
            f"{group['count']:>8,}  "
            f"{group['sender']}"
        )

        total_messages += group["count"]

    print("-" * 78)

    print(
        f"Groups:   {len(selected_numbers):,}"
    )

    print(
        f"Messages: {total_messages:,}"
    )


def apply_label_to_messages(
    service,
    message_ids,
    label_id,
):
    """Apply the current session label in batches of 20."""

    total = len(message_ids)

    if total == 0:
        return

    for start in range(
        0,
        total,
        LABEL_BATCH_SIZE,
    ):
        batch = message_ids[
            start:start + LABEL_BATCH_SIZE
        ]

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
            start + LABEL_BATCH_SIZE,
            total,
        )

        print(
            f"\rProtecting messages: "
            f"{completed:,}/{total:,}",
            end="",
            flush=True,
        )

    print()


def review_mode():
    """Select sender groups to protect.

    Review Mode NEVER deletes messages.

    It creates one unique session label and applies it
    only to the sender groups selected during this run.

    Messages already marked as trashed in the local
    database are excluded.
    """

    print()
    print("=" * 78)
    print("SAMUDRA MANTHAN — REVIEW MODE")
    print("=" * 78)
    print()

    print(
        "Review Mode NEVER deletes messages."
    )

    print(
        "It only protects selected sender groups "
        "with a temporary session label."
    )

    print()

    # One unique label for this complete review session.
    label_name, label_id = create_session_label()

    print(
        f"Session label: {label_name}"
    )

    print()

    print(
        "Loading local message index..."
    )

    groups = get_sender_groups()

    total_messages = sum(
        group["count"]
        for group in groups
    )

    print(
        f"Loaded {total_messages:,} active messages "
        f"from local database."
    )

    print(
        f"Found {len(groups):,} active sender groups."
    )

    if not groups:
        print()
        print("No active messages found.")
        return label_name

    # ---------------------------------------------------------
    # SHOW ALL ACTIVE GROUPS FIRST
    # ---------------------------------------------------------

    display_groups(groups)

    # ---------------------------------------------------------
    # USER SELECTS GROUPS
    # ---------------------------------------------------------

    print()
    print("=" * 78)
    print("SELECT GROUPS TO PROTECT")
    print("=" * 78)
    print()

    print(
        "Enter sender numbers separated by commas."
    )

    print(
        "Ranges are supported: 1-5, 10-15"
    )

    print()

    print("Examples:")
    print("  1,7,18")
    print("  1-5,10,20-25")

    print()

    print("Commands:")
    print(
        "  [Q] Quit without protecting anything"
    )

    print()

    while True:
        value = input(
            "Groups to protect > "
        ).strip()

        if value.lower() == "q":
            print()
            print("Review cancelled.")
            print(
                f"Session label: {label_name}"
            )
            return label_name

        try:
            selected_numbers = parse_selection(
                value,
                len(groups),
            )

        except ValueError as exc:
            print()
            print(
                f"Invalid selection: {exc}"
            )
            print(
                "Try again."
            )
            continue

        if not selected_numbers:
            print(
                "No groups selected."
            )
            continue

        break

    # ---------------------------------------------------------
    # SHOW SELECTION BEFORE TOUCHING GMAIL
    # ---------------------------------------------------------

    display_selection(
        groups,
        selected_numbers,
    )

    # ---------------------------------------------------------
    # COLLECT SENDERS
    # ---------------------------------------------------------

    selected_senders = [
        groups[number - 1]["sender"]
        for number in selected_numbers
    ]

    print()

    print(
        "These messages will receive:"
    )

    print(
        f"  {label_name}"
    )

    print()

    print(
        "Review Mode will NOT delete them."
    )

    print()

    while True:
        confirmation = input(
            "Apply protection? [Y/n] > "
        ).strip().lower()

        if confirmation in (
            "",
            "y",
            "yes",
        ):
            break

        if confirmation in (
            "n",
            "no",
        ):
            print()
            print(
                "Protection cancelled."
            )
            print(
                f"Session label: {label_name}"
            )
            return label_name

        print(
            "Please enter Y or N."
        )

    # ---------------------------------------------------------
    # LOAD ONLY SELECTED ACTIVE MESSAGE IDS FROM SQLITE
    # ---------------------------------------------------------

    print()

    print(
        "Loading selected message IDs "
        "from local database..."
    )

    message_ids = get_message_ids_for_senders(
        selected_senders
    )

    print(
        f"Selected messages: "
        f"{len(message_ids):,}"
    )

    if not message_ids:
        print(
            "No active message IDs found."
        )
        return label_name

    # ---------------------------------------------------------
    # APPLY CURRENT SESSION LABEL
    # ---------------------------------------------------------

    print()

    print(
        f"Applying {label_name}..."
    )

    service = get_gmail_service()

    apply_label_to_messages(
        service,
        message_ids,
        label_id,
    )

    # ---------------------------------------------------------
    # FINISHED
    # ---------------------------------------------------------

    print()

    print("=" * 78)
    print("REVIEW COMPLETE")
    print("=" * 78)

    print()

    print(
        f"Session label: {label_name}"
    )

    print(
        f"Protected groups: "
        f"{len(selected_numbers):,}"
    )

    print(
        f"Protected messages: "
        f"{len(message_ids):,}"
    )

    print()

    print(
        "Only this session label should be used "
        "by the next Delete Mode run:"
    )

    print(
        f"  {label_name}"
    )

    print()

    return label_name


if __name__ == "__main__":
    review_mode()