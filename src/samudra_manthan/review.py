from samudra_manthan.gmail.auth import get_gmail_account
from samudra_manthan.gmail.client import get_gmail_service
from samudra_manthan.gmail.labels import create_session_label
from samudra_manthan.storage.database import get_connection

LABEL_BATCH_SIZE = 20


def get_sender_groups():
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT sender_email, COUNT(*) AS message_count
        FROM messages
        WHERE sender_email IS NOT NULL AND sender_email != '' AND trashed = 0
        GROUP BY sender_email
        ORDER BY message_count DESC, sender_email ASC
        """
    ).fetchall()
    connection.close()

    return [{"email": row["sender_email"], "count": row["message_count"]} for row in rows]


def get_recipient_groups(account_email: str):
    """Load active recipient groups for messages sent by the user."""
    connection = get_connection()
    rows = connection.execute(
        """
        SELECT recipient_email, COUNT(*) AS message_count
        FROM messages
        WHERE recipient_email IS NOT NULL AND recipient_email != '' 
          AND sender_email = ? AND trashed = 0
        GROUP BY recipient_email
        ORDER BY message_count DESC, recipient_email ASC
        """,
        (account_email,)
    ).fetchall()
    connection.close()

    return [{"email": row["recipient_email"], "count": row["message_count"]} for row in rows]


def get_message_ids_for_senders(senders):
    if not senders:
        return []
    connection = get_connection()
    placeholders = ",".join("?" for _ in senders)
    rows = connection.execute(
        f"SELECT id FROM messages WHERE sender_email IN ({placeholders}) AND trashed = 0",
        list(senders),
    ).fetchall()
    connection.close()
    return [row["id"] for row in rows]


def get_message_ids_for_recipients(recipients, account_email: str):
    if not recipients:
        return []
    connection = get_connection()
    placeholders = ",".join("?" for _ in recipients)
    params = list(recipients)
    params.append(account_email)
    
    rows = connection.execute(
        f"SELECT id FROM messages WHERE recipient_email IN ({placeholders}) AND sender_email = ? AND trashed = 0",
        params,
    ).fetchall()
    connection.close()
    return [row["id"] for row in rows]


def display_groups(groups, label="SENDER"):
    print()
    print("=" * 78)
    print(f"SAMUDRA MANTHAN — {label} GROUPS")
    print("=" * 78)

    total_messages = sum(group["count"] for group in groups)
    print(f"\nMessages: {total_messages:,}   {label}s: {len(groups):,}\n")
    print(f"{'#':>4}  {'MESSAGES':>8}  {label}")
    print("-" * 78)

    for number, group in enumerate(groups, start=1):
        print(f"{number:>4}  {group['count']:>8,}  {group['email']}")
    print("-" * 78)


def parse_selection(value, total):
    selected = set()
    parts = [part.strip() for part in value.split(",") if part.strip()]

    for part in parts:
        if "-" in part:
            pieces = part.split("-", 1)
            if len(pieces) != 2:
                raise ValueError(f"Invalid range: {part}")
            try:
                start = int(pieces[0])
                end = int(pieces[1])
            except ValueError:
                raise ValueError(f"Invalid range: {part}")

            if start > end:
                start, end = end, start
            if start < 1 or end > total:
                raise ValueError(f"Range {part} is outside 1-{total}")
            selected.update(range(start, end + 1))
        else:
            try:
                number = int(part)
            except ValueError:
                raise ValueError(f"Invalid group number: {part}")
            if number < 1 or number > total:
                raise ValueError(f"Number {number} is outside 1-{total}")
            selected.add(number)

    return sorted(selected)


def display_selection(groups, selected_numbers, label="SENDER"):
    print()
    print("=" * 78)
    print("SELECTED GROUPS")
    print("=" * 78)

    total_messages = 0
    for number in selected_numbers:
        group = groups[number - 1]
        print(f"{number:>4}  {group['count']:>8,}  {group['email']}")
        total_messages += group["count"]

    print("-" * 78)
    print(f"Groups:   {len(selected_numbers):,}")
    print(f"Messages: {total_messages:,}")


def apply_label_to_messages(service, message_ids, label_id):
    total = len(message_ids)
    if total == 0:
        return

    for start in range(0, total, LABEL_BATCH_SIZE):
        batch = message_ids[start:start + LABEL_BATCH_SIZE]
        (
            service.users()
            .messages()
            .batchModify(
                userId="me",
                body={"ids": batch, "addLabelIds": [label_id]},
            )
            .execute()
        )
        completed = min(start + LABEL_BATCH_SIZE, total)
        print(f"\rProtecting messages: {completed:,}/{total:,}", end="", flush=True)
    print()


def review_mode():
    print("\n" + "=" * 78)
    print("SAMUDRA MANTHAN — REVIEW MODE (INBOX)")
    print("=" * 78 + "\n")
    print("Review Mode NEVER deletes messages.")
    print("It only protects selected sender groups with a temporary session label.\n")

    label_name, label_id = create_session_label()
    print(f"Session label: {label_name}\n")
    print("Loading local message index...")

    groups = get_sender_groups()
    total_messages = sum(group["count"] for group in groups)

    print(f"Loaded {total_messages:,} active messages from local database.")
    print(f"Found {len(groups):,} active sender groups.")

    if not groups:
        print("\nNo active messages found.")
        return label_name

    display_groups(groups, label="SENDER")
    
    print("\n" + "=" * 78)
    print("SELECT GROUPS TO PROTECT")
    print("=" * 78 + "\n")
    print("Enter sender numbers separated by commas. Ranges are supported (1-5).")
    print("Commands: [Q] Quit without protecting anything\n")

    while True:
        value = input("Groups to protect > ").strip()
        if value.lower() == "q":
            print(f"\nReview cancelled.\nSession label: {label_name}")
            return label_name
        try:
            selected_numbers = parse_selection(value, len(groups))
        except ValueError as exc:
            print(f"\nInvalid selection: {exc}\nTry again.")
            continue
        if not selected_numbers:
            print("No groups selected.")
            continue
        break

    display_selection(groups, selected_numbers, label="SENDER")

    selected_emails = [groups[number - 1]["email"] for number in selected_numbers]
    print(f"\nThese messages will receive:\n  {label_name}\n\nReview Mode will NOT delete them.\n")

    while True:
        confirmation = input("Apply protection? [Y/n] > ").strip().lower()
        if confirmation in ("", "y", "yes"):
            break
        if confirmation in ("n", "no"):
            print(f"\nProtection cancelled.\nSession label: {label_name}")
            return label_name
        print("Please enter Y or N.")

    print("\nLoading selected message IDs from local database...")
    message_ids = get_message_ids_for_senders(selected_emails)
    print(f"Selected messages: {len(message_ids):,}")

    if not message_ids:
        print("No active message IDs found.")
        return label_name

    print(f"\nApplying {label_name}...")
    service = get_gmail_service()
    apply_label_to_messages(service, message_ids, label_id)

    print("\n" + "=" * 78)
    print("REVIEW COMPLETE")
    print("=" * 78 + "\n")
    print(f"Session label: {label_name}")
    print(f"Protected groups: {len(selected_numbers):,}")
    print(f"Protected messages: {len(message_ids):,}\n")
    print(f"Only this session label should be used by the next Delete Mode run:\n  {label_name}\n")
    return label_name


def review_sent_mode():
    print("\n" + "=" * 78)
    print("SAMUDRA MANTHAN — REVIEW MODE (SENTBOX)")
    print("=" * 78 + "\n")
    print("Review Mode NEVER deletes messages.")
    print("It only protects selected recipient groups with a temporary session label.\n")

    account_email = get_gmail_account()
    label_name, label_id = create_session_label()
    print(f"Session label: {label_name}\n")
    print("Loading local message index for sent mail...")

    groups = get_recipient_groups(account_email)
    total_messages = sum(group["count"] for group in groups)

    print(f"Loaded {total_messages:,} active sent messages from local database.")
    print(f"Found {len(groups):,} active recipient groups.")

    if not groups:
        print("\nNo active sent messages found.")
        return label_name

    display_groups(groups, label="RECIPIENT")
    
    print("\n" + "=" * 78)
    print("SELECT GROUPS TO PROTECT")
    print("=" * 78 + "\n")
    print("Enter recipient numbers separated by commas. Ranges are supported (1-5).")
    print("Commands: [Q] Quit without protecting anything\n")

    while True:
        value = input("Groups to protect > ").strip()
        if value.lower() == "q":
            print(f"\nReview cancelled.\nSession label: {label_name}")
            return label_name
        try:
            selected_numbers = parse_selection(value, len(groups))
        except ValueError as exc:
            print(f"\nInvalid selection: {exc}\nTry again.")
            continue
        if not selected_numbers:
            print("No groups selected.")
            continue
        break

    display_selection(groups, selected_numbers, label="RECIPIENT")

    selected_emails = [groups[number - 1]["email"] for number in selected_numbers]
    print(f"\nThese messages will receive:\n  {label_name}\n\nReview Mode will NOT delete them.\n")

    while True:
        confirmation = input("Apply protection? [Y/n] > ").strip().lower()
        if confirmation in ("", "y", "yes"):
            break
        if confirmation in ("n", "no"):
            print(f"\nProtection cancelled.\nSession label: {label_name}")
            return label_name
        print("Please enter Y or N.")

    print("\nLoading selected message IDs from local database...")
    message_ids = get_message_ids_for_recipients(selected_emails, account_email)
    print(f"Selected messages: {len(message_ids):,}")

    if not message_ids:
        print("No active message IDs found.")
        return label_name

    print(f"\nApplying {label_name}...")
    service = get_gmail_service()
    apply_label_to_messages(service, message_ids, label_id)

    print("\n" + "=" * 78)
    print("REVIEW COMPLETE")
    print("=" * 78 + "\n")
    print(f"Session label: {label_name}")
    print(f"Protected groups: {len(selected_numbers):,}")
    print(f"Protected messages: {len(message_ids):,}\n")
    print(f"Only this session label should be used by the next Delete Mode run:\n  {label_name}\n")
    return label_name

if __name__ == "__main__":
    review_mode()