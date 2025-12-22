# Streamlit Cloud Deployment Guide

## Step 1: Create a GitHub Account (if you don't have one)
1. Go to https://github.com
2. Sign up for a free account

## Step 2: Create a New Repository
1. Click the "+" icon in the top right
2. Select "New repository"
3. Name it: `Fail_testing_12a`
4. Make it **Public** (required for free Streamlit Cloud)
5. Don't initialize with README (we already have files)
6. Click "Create repository"

## Step 3: Push Your Code to GitHub

### Option A: Using GitHub Desktop (Easiest)
1. Download GitHub Desktop: https://desktop.github.com
2. Install and sign in
3. Click "File" → "Add Local Repository"
4. Select this folder: `C:\Users\JMJsm\Documents\AI\Bet-tracker`
5. Click "Publish repository"
6. Make sure it's set to Public
7. Click "Publish repository"

### Option B: Using Git Command Line
Open PowerShell in this folder and run:

```powershell
git init
git add .
git commit -m "Initial commit - Bet Tracker App"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/Fail_testing_12a.git
git push -u origin main
```

(Replace `YOUR_USERNAME` with your GitHub username)

## Step 4: Deploy to Streamlit Cloud
1. Go to https://share.streamlit.io
2. Sign in with your GitHub account
3. Click "New app"
4. Select your repository: `Fail_testing_12a`
5. Select branch: `main`
6. Main file path: `bet_tracker.py`
7. Click "Deploy!"

## Step 5: Configure Secrets (API Key)
1. In Streamlit Cloud, go to your app settings
2. Click "Secrets"
3. Add your API key:
   ```
   API_KEY = "5d01a63b3ba3428b2b1b677305ef7c3b"
   ```
4. Or modify `bet_tracker.py` to use Streamlit secrets:
   ```python
   API_KEY = st.secrets.get("API_KEY", "5d01a63b3ba3428b2b1b677305ef7c3b")
   ```

## Step 6: Access Your App
Once deployed, you'll get a URL like:
`https://your-app-name.streamlit.app`

You can access this from **any device** including your iPhone!

## Notes:
- The app will be public (anyone with the URL can access it)
- Data is stored in the app's memory (resets on restart)
- For persistent data, consider using a database or file storage service

