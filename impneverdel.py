from samudra_manthan.gmail.client import get_gmail_service

service = get_gmail_service()

# Find NEVERDELETE
labels = service.users().labels().list(userId="me").execute()["labels"]

neverdelete_id = next(
    x["id"] for x in labels
    if x["name"] == "NEVERDELETE"
)

# Get all Important messages
ids = []
page_token = None

while True:
    result = service.users().messages().list(
        userId="me",
        labelIds=["IMPORTANT"],
        maxResults=500,
        pageToken=page_token,
    ).execute()

    ids += [m["id"] for m in result.get("messages", [])]

    page_token = result.get("nextPageToken")

    if not page_token:
        break

print(f"Important messages: {len(ids)}")

# Add NEVERDELETE
for i in range(0, len(ids), 500):
    service.users().messages().batchModify(
        userId="me",
        body={
            "ids": ids[i:i + 500],
            "addLabelIds": [neverdelete_id],
        },
    ).execute()

print("Done. All Important messages are marked NEVERDELETE.")
