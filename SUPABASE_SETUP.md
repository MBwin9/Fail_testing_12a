# Supabase Setup - Free Database (No Service Account Keys Needed!)

## Why Supabase?
- ✅ **Free tier** - Perfect for personal projects
- ✅ **No service account keys** - Uses simple API keys
- ✅ **PostgreSQL database** - Reliable and fast
- ✅ **Easy setup** - Takes 5 minutes
- ✅ **Persistent storage** - Data never gets deleted

---

## STEP 1: Create Supabase Account (2 minutes)

1. Go to https://supabase.com
2. Click **"Start your project"** or **"Sign up"**
3. Sign up with GitHub (easiest) or email
4. Verify your email if needed

**✅ Checkpoint**: You should be logged into Supabase dashboard

---

## STEP 2: Create a New Project (2 minutes)

1. Click **"New Project"** (green button)
2. Organization: Create new or use existing
3. Project name: **"bet-tracker"** (or any name)
4. Database password: **Create a strong password** (save it somewhere!)
5. Region: Choose closest to you (e.g., "US East (North Virginia)")
6. Click **"Create new project"**
7. Wait 2-3 minutes for project to be created

**✅ Checkpoint**: You should see your project dashboard

---

## STEP 3: Create the Bets Table (3 minutes)

1. In your Supabase project, click **"Table Editor"** (left sidebar)
2. Click **"Create a new table"**
3. Table name: **"bets"**
4. **Uncheck** "Enable Row Level Security" (for simplicity)
5. Click **"Save"**

### Add Columns:
Click **"Add column"** for each of these:

1. **id** (Integer, Primary Key, Auto-increment) ✅
2. **user** (Text)
3. **game** (Text)
4. **bet_type** (Text)
5. **stake** (Numeric)
6. **team** (Text, nullable)
7. **spread** (Numeric, nullable)
8. **total** (Numeric, nullable)
9. **direction** (Text, nullable)
10. **no_juice** (Boolean, default: false)
11. **result** (Text, nullable)
12. **settled** (Boolean, default: false)
13. **profit** (Numeric, default: 0)
14. **payout** (Numeric, default: 0)
15. **created_at** (Text)
16. **settled_at** (Text, nullable)
17. **final_score** (Text, nullable)

**Tip**: For nullable fields, make sure "Is Nullable" is checked.

Click **"Save"** when done.

**✅ Checkpoint**: You should have a "bets" table with all columns

---

## STEP 4: Get Your API Keys (1 minute)

1. In Supabase dashboard, click **"Settings"** (gear icon, bottom left)
2. Click **"API"** (under Project Settings)
3. You'll see:
   - **Project URL** (looks like: `https://xxxxx.supabase.co`)
   - **anon/public key** (long string starting with `eyJ...`)

**Copy both of these - you'll need them!**

**✅ Checkpoint**: You should have your URL and API key copied

---

## STEP 5: Add Secrets to Streamlit Cloud (2 minutes)

1. Go to https://share.streamlit.io
2. Find your app and click **"⋮"** (three dots) → **"Settings"**
3. Click **"Secrets"** (left sidebar)
4. Add these two lines:

```toml
SUPABASE_URL = "YOUR_PROJECT_URL_HERE"
SUPABASE_KEY = "YOUR_ANON_KEY_HERE"
```

Replace:
- `YOUR_PROJECT_URL_HERE` with your Project URL from Step 4
- `YOUR_ANON_KEY_HERE` with your anon/public key from Step 4

5. Click **"Save"**

**✅ Checkpoint**: Secrets should be saved

---

## STEP 6: Deploy Updated Code

The code is already updated and pushed to GitHub! Streamlit Cloud should automatically redeploy.

If not, go to your Streamlit Cloud app and click **"Reboot app"**

**✅ Checkpoint**: App should be running

---

## STEP 7: Test It! (1 minute)

1. Open your Streamlit app
2. Add a test bet
3. Refresh the page - **your bet should still be there!** ✅
4. Go back to Supabase → Table Editor → bets table
5. You should see your bet data there too!

---

## Troubleshooting

### "relation 'bets' does not exist"
- Make sure you created the table in Step 3
- Check the table name is exactly "bets" (lowercase)

### "permission denied"
- Make sure Row Level Security is disabled (Step 3)
- Or enable it and create a policy (more advanced)

### "invalid API key"
- Double-check you copied the **anon/public** key (not the service_role key)
- Make sure there are no extra spaces in the secrets

### Data not saving
- Check Streamlit Cloud logs (click "Manage app" → "Logs")
- Make sure the table columns match what the code expects
- Try rebooting the app

---

## Need Help?

If you get stuck, let me know which step and what error you're seeing!

## Free Tier Limits

Supabase free tier includes:
- 500 MB database storage (plenty for bets!)
- 2 GB bandwidth per month
- Unlimited API requests

Perfect for your use case! 🎉

