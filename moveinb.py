from samudra_manthan.gmail.client import get_gmail_service

service = get_gmail_service()

# Find NEVERDELETE
labels = service.users().labels().list(
    userId="me"
).execute()["labels"]

neverdelete_id = next(
    x["id"]
    for x in labels
    if x["name"] == "NEVERDELETE"
)

# Find all NEVERDELETE messages
ids = []
page_token = None

while True:
    result = service.users().messages().list(
        userId="me",
        labelIds=[neverdelete_id],
        maxResults=500,
        pageToken=page_token,
    ).execute()

    ids.extend(
        message["id"]
        for message in result.get("messages", [])
    )

    page_token = result.get("nextPageToken")

    if not page_token:
        break

print(f"NEVERDELETE messages: {len(ids):,}")

# Put them into Inbox
for i in range(0, len(ids), 500):
    batch = ids[i:i + 500]

    service.users().messages().batchModify(
        userId="me",
        body={
            "ids": batch,
            "addLabelIds": ["INBOX"],
        },
    ).execute()

    print(
        f"Moved to Inbox: "
        f"{min(i + len(batch), len(ids)):,}/{len(ids):,}"
    )

print("Done.")
