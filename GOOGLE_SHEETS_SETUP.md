# Google Sheets Setup for Persistent Data Storage

## Why Google Sheets?
Streamlit Cloud uses ephemeral storage - files get wiped on restart. Google Sheets provides free, persistent cloud storage that works perfectly for this app.

## Setup Instructions

### Step 1: Create a Google Sheet
1. Go to https://sheets.google.com
2. Create a new blank spreadsheet
3. Name it: "Bet Tracker Data" (or any name you like)
4. **Copy the URL** from your browser (it looks like: `https://docs.google.com/spreadsheets/d/XXXXX/edit`)

### Step 2: Create a Google Cloud Project & Service Account
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Enable Google Sheets API:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Sheets API"
   - Click "Enable"
4. Enable Google Drive API:
   - Search for "Google Drive API"
   - Click "Enable"
5. Create Service Account:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "Service Account"
   - Name it: "bet-tracker-service"
   - Click "Create and Continue"
   - Skip role assignment, click "Done"
6. Create Key:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose "JSON"
   - Download the JSON file (keep it safe!)

### Step 3: Share Google Sheet with Service Account
1. Open your Google Sheet
2. Click "Share" button
3. **IMPORTANT**: Add the service account email (found in the JSON file as `client_email`)
   - It looks like: `bet-tracker-service@your-project.iam.gserviceaccount.com`
4. Give it "Editor" permissions
5. Click "Send"

### Step 4: Add Secrets to Streamlit Cloud
1. Go to your Streamlit Cloud app
2. Click "Settings" (gear icon)
3. Click "Secrets"
4. Add these secrets:

```toml
GOOGLE_SHEETS_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

[GOOGLE_CREDENTIALS]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
```

**Copy the entire contents of the downloaded JSON file into the `[GOOGLE_CREDENTIALS]` section.**

### Step 5: Deploy
1. Push your updated code to GitHub
2. Streamlit Cloud will automatically redeploy
3. Your data will now persist!

## Alternative: Simple JSON File (Temporary Solution)
If you don't want to set up Google Sheets right now, the app will still work but data will reset on restart. For a quick test, you can:
- Use the app locally (data saves to `bets_data.json`)
- Or accept that cloud data resets (good for testing)

## Troubleshooting
- **"Permission denied"**: Make sure you shared the sheet with the service account email
- **"API not enabled"**: Enable both Google Sheets API and Google Drive API
- **"Invalid credentials"**: Double-check the JSON content in Streamlit secrets

