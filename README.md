# Samudra Manthan

An open-source, high-performance, and privacy-first Gmail cleanup utility. 

Instead of mindlessly deleting emails based on search queries, Samudra Manthan uses an inverted **"Review & Protect"** philosophy: you review grouped senders, protect the ones you want to keep, and bulk-trash the rest in seconds.

## Features
* **Blazing Fast Scans:** Uses Google's `BatchHttpRequest` (100 messages/call) and caches metadata in a local SQLite database to prevent redundant network calls.
* **Review & Protect:** Generates unique session labels (`SM_KEEP_*`) to protect essential senders before any deletion occurs.
* **Bulk Deletion:** Bypasses standard rate limits by pushing up to 1,000 messages to the Trash per API call with exponential backoff.
* **Inbox & Sentbox Isolation:** Independently scan, review, and clean incoming mail and outgoing mail.
* **Multi-Account Support:** Seamlessly switch between different Gmail accounts. All data is isolated in account-specific local databases.

## Setup
1. Clone the repository.
2. Create and activate a virtual environment.
3. Install the project in editable mode:
   ```bash
   pip install -e .
   ```
4. Place your Google OAuth `credentials.json` inside the `config/` directory.

## Usage
Run the CLI tool from your terminal:
```bash
python -m samudra_manthan
```

**The Workflow:**
1. **Scan / Refresh:** Pulls your latest mailbox state into the local SQLite database.
2. **Review & Protect:** Displays grouped senders/recipients. Select the ones you want to keep.
3. **Delete:** Safely moves all *unprotected* emails to the Gmail Trash.
4. **Empty Trash:** Permanently wipes the Gmail Trash folder.

## Privacy
All processing is done locally on your machine. Your emails are never sent to a third-party server. The local SQLite databases (`data/accounts/`) remain entirely on your device.
