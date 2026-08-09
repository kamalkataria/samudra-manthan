import time
from collections import Counter
from email.utils import parseaddr, parsedate_to_datetime

from googleapiclient.errors import HttpError
from googleapiclient.http import BatchHttpRequest

from samudra_manthan.storage.database import (
    initialize_database,
    save_messages,
    rebuild_sender_counts,
)

from .client import get_gmail_service


# ---------------------------------------------------------
# SCAN SETTINGS
# ---------------------------------------------------------

LIST_PAGE_SIZE = 500
BATCH_SIZE = 100
MAX_RETRIES = 5
INITIAL_RETRY_DELAY = 1.0


# ---------------------------------------------------------
# LIST MESSAGE IDS
# ---------------------------------------------------------

def list_message_ids(service):
    """Return all message IDs in the current Gmail mailbox."""

    message_ids = []
    page_token = None

    while True:
        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                pageToken=page_token,
                maxResults=LIST_PAGE_SIZE,
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


# ---------------------------------------------------------
# DATE NORMALIZATION
# ---------------------------------------------------------

def _normalize_date(value):
    """Convert an email Date header to ISO-8601."""
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError):
        return None


# ---------------------------------------------------------
# MESSAGE PARSING
# ---------------------------------------------------------

def _parse_message(message):
    """Convert Gmail metadata into a small Python dictionary."""

    headers = {
        header["name"].lower(): header["value"]
        for header in (
            message
            .get("payload", {})
            .get("headers", [])
        )
    }

    sender_name, sender_email = parseaddr(headers.get("from", ""))
    recipient_name, recipient_email = parseaddr(headers.get("to", ""))

    return {
        "id": message["id"],
        "thread_id": message.get("threadId"),
        "sender_name": sender_name,
        "sender_email": sender_email.lower(),
        "recipient_email": recipient_email.lower(),
        "subject": headers.get("subject", ""),
        "date": _normalize_date(headers.get("date", "")),
        "labels": message.get("labelIds", []),
    }


# ---------------------------------------------------------
# ERROR HELPERS
# ---------------------------------------------------------

def _is_retryable_error(exception):
    if not isinstance(exception, HttpError):
        return False
    status = getattr(exception.resp, "status", None)
    return status in (429, 500, 502, 503, 504)


# ---------------------------------------------------------
# SINGLE MESSAGE RETRY
# ---------------------------------------------------------

def _get_message_with_retry(service, message_id):
    delay = INITIAL_RETRY_DELAY
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                )
                .execute()
            )
        except HttpError as exc:
            if not _is_retryable_error(exc):
                raise
            if attempt >= MAX_RETRIES:
                raise

            print(
                f"\nTemporary Gmail error for {message_id} "
                f"(attempt {attempt}/{MAX_RETRIES}). "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            delay *= 2

    raise RuntimeError(f"Unable to read Gmail message {message_id}")


# ---------------------------------------------------------
# BATCH METADATA
# ---------------------------------------------------------

def get_message_metadata_batch(service, message_ids):
    messages = []
    failed_message_ids = []
    total = len(message_ids)

    def callback(request_id, response, exception):
        if exception is not None:
            failed_message_ids.append(request_id)
            print(f"\nWarning: batch read failed for {request_id}: {exception}")
            return
        try:
            messages.append(_parse_message(response))
        except Exception as exc:
            print(f"\nWarning: could not parse message {request_id}: {exc}")

    for start in range(0, total, BATCH_SIZE):
        batch_ids = message_ids[start:start + BATCH_SIZE]
        batch = BatchHttpRequest(
            callback=callback,
            batch_uri="https://gmail.googleapis.com/batch/gmail/v1",
        )

        for message_id in batch_ids:
            request = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date"],
                )
            )
            batch.add(request, request_id=message_id)

        try:
            batch.execute()
        except Exception as exc:
            print(f"\nWarning: batch request failed: {exc}")
            for message_id in batch_ids:
                if message_id not in failed_message_ids:
                    failed_message_ids.append(message_id)

        processed = min(start + len(batch_ids), total)
        print(f"\rReading metadata: {processed:,}/{total:,}", end="", flush=True)

    if failed_message_ids:
        print(f"\n\nRetrying {len(failed_message_ids):,} temporarily failed messages...\n")
        permanently_failed = []

        for number, message_id in enumerate(failed_message_ids, start=1):
            try:
                message = _get_message_with_retry(service, message_id)
                messages.append(_parse_message(message))
            except Exception as exc:
                permanently_failed.append(message_id)
                print(f"\nWarning: permanently unable to read {message_id}: {exc}")

            print(f"\rRetrying messages: {number:,}/{len(failed_message_ids):,}", end="", flush=True)
        print()

        if permanently_failed:
            print("\nSome messages could not be read after retries:")
            print(f"  Failed: {len(permanently_failed):,}")
            print("They will be retried during the next mailbox scan.")
        else:
            print("\nAll temporarily failed messages were recovered.")

    return messages


# ---------------------------------------------------------
# SENDER COUNTS
# ---------------------------------------------------------

def count_senders(messages):
    return Counter(
        message["sender_email"]
        for message in messages
        if message["sender_email"]
    )


# ---------------------------------------------------------
# FULL MAILBOX SCAN
# ---------------------------------------------------------

def scan_mailbox():
    print("\nInitializing account database...")
    initialize_database()

    service = get_gmail_service()
    print("\nReading message list...")
    message_ids = list_message_ids(service)
    print(f"Found {len(message_ids):,} messages.")

    if not message_ids:
        print("\nMailbox contains no messages.")
        rebuild_sender_counts()
        return [], Counter()

    print("\nReading message metadata...")
    messages = get_message_metadata_batch(service, message_ids)
    print(f"\nSuccessfully read {len(messages):,}/{len(message_ids):,} messages.")

    print("\nSaving messages to local database...")
    save_messages(messages)

    print("\nBuilding sender statistics...")
    rebuild_sender_counts()
    sender_counts = count_senders(messages)

    print(f"\nLocal index now contains {len(messages):,} scanned messages.")
    print(f"Unique senders in this scan: {len(sender_counts):,}")
    return messages, sender_counts