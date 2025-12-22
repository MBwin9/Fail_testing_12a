# Google Sheets Setup - Step by Step Guide

## Overview
This will allow your bet data to persist permanently in the cloud, so it won't reset when the app restarts.

---

## STEP 1: Create a Google Sheet (2 minutes)

1. Go to https://sheets.google.com
2. Click the **"+"** button or "Blank" to create a new spreadsheet
3. Name it: **"Bet Tracker Data"** (or any name you like)
4. **IMPORTANT**: Copy the URL from your browser
   - It looks like: `https://docs.google.com/spreadsheets/d/1ABC123xyz.../edit`
   - You'll need this later!

**✅ Checkpoint**: You should have a blank Google Sheet with a URL copied.

---

## STEP 2: Create Google Cloud Project (5 minutes)

1. Go to https://console.cloud.google.com
2. Sign in with your Google account
3. Click the project dropdown at the top (it might say "Select a project")
4. Click **"NEW PROJECT"**
5. Project name: **"bet-tracker"** (or any name)
6. Click **"CREATE"**
7. Wait a few seconds, then select your new project from the dropdown

**✅ Checkpoint**: You should see your project name at the top of the page.

---

## STEP 3: Enable APIs (2 minutes)

1. In Google Cloud Console, go to **"APIs & Services"** → **"Library"** (left sidebar)
2. Search for **"Google Sheets API"**
3. Click on it and click **"ENABLE"**
4. Go back to Library
5. Search for **"Google Drive API"**
6. Click on it and click **"ENABLE"**

**✅ Checkpoint**: Both APIs should show as "Enabled"

---

## STEP 4: Create Service Account (3 minutes)

1. In Google Cloud Console, go to **"APIs & Services"** → **"Credentials"** (left sidebar)
2. Click **"+ CREATE CREDENTIALS"** at the top
3. Select **"Service account"**
4. Service account name: **"bet-tracker-service"**
5. Service account ID: (auto-filled, leave as is)
6. Click **"CREATE AND CONTINUE"**
7. Skip "Grant this service account access to project" - click **"CONTINUE"**
8. Skip "Grant users access" - click **"DONE"**

**✅ Checkpoint**: You should see your service account in the list.

---

## STEP 5: Create and Download Key (2 minutes)

1. Click on your service account name (bet-tracker-service)
2. Go to the **"Keys"** tab
3. Click **"ADD KEY"** → **"Create new key"**
4. Select **"JSON"**
5. Click **"CREATE"**
6. **IMPORTANT**: A JSON file will download automatically - **SAVE THIS FILE SAFELY!**
   - It contains your credentials
   - Don't share it publicly
   - You'll need it in the next step

**✅ Checkpoint**: You should have downloaded a JSON file (looks like: `bet-tracker-xxxxx.json`)

---

## STEP 6: Share Google Sheet with Service Account (1 minute)

1. Open the JSON file you just downloaded
2. Find the line that says `"client_email"` - it looks like:
   ```json
   "client_email": "bet-tracker-service@your-project.iam.gserviceaccount.com"
   ```
3. **Copy that email address** (the whole thing)
4. Go back to your Google Sheet
5. Click the **"Share"** button (top right)
6. Paste the email address in the "Add people and groups" field
7. Make sure it says **"Editor"** (not Viewer)
8. **Uncheck** "Notify people" (optional)
9. Click **"Share"**

**✅ Checkpoint**: The service account email should be listed as an editor in your sheet.

---

## STEP 7: Add Secrets to Streamlit Cloud (5 minutes)

1. Go to https://share.streamlit.io
2. Sign in and find your app
3. Click the **"⋮"** (three dots) next to your app → **"Settings"**
4. Click **"Secrets"** in the left sidebar
5. You'll see a text editor - replace everything with this template:

```toml
GOOGLE_SHEETS_URL = "PASTE_YOUR_SHEET_URL_HERE"

[GOOGLE_CREDENTIALS]
```

6. **For GOOGLE_SHEETS_URL**: Paste the URL you copied in Step 1
7. **For GOOGLE_CREDENTIALS**: Open the JSON file you downloaded and copy the ENTIRE contents
8. Paste it after `[GOOGLE_CREDENTIALS]` - it should look like:

```toml
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/1ABC123xyz.../edit"

[GOOGLE_CREDENTIALS]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_KEY_HERE\n-----END PRIVATE KEY-----\n"
client_email = "bet-tracker-service@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

9. Click **"Save"**

**✅ Checkpoint**: Secrets should be saved successfully.

---

## STEP 8: Update and Deploy Code (2 minutes)

1. Make sure your code is pushed to GitHub (with the Google Sheets code)
2. Go back to Streamlit Cloud
3. Your app should automatically redeploy, or click **"Reboot app"**
4. Wait 1-2 minutes for deployment

**✅ Checkpoint**: App should be running with Google Sheets integration.

---

## STEP 9: Test It!

1. Open your Streamlit app
2. Add a test bet
3. Refresh the page - **your bet should still be there!** ✅
4. Check your Google Sheet - you should see the data there too!

---

## Troubleshooting

### "Permission denied" error
- Make sure you shared the Google Sheet with the service account email
- The email should have "Editor" permissions

### "API not enabled" error
- Go back to Google Cloud Console
- Make sure both Google Sheets API and Google Drive API are enabled

### "Invalid credentials" error
- Double-check that you copied the entire JSON file contents correctly
- Make sure there are no extra spaces or characters
- The private_key should have `\n` for newlines

### Data not saving
- Check Streamlit Cloud logs (click "Manage app" → "Logs")
- Make sure the secrets are saved correctly
- Try rebooting the app

---

## Need Help?

If you get stuck at any step, let me know which step and what error you're seeing!

