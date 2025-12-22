# 🏈 Brothers Bet Tracker

A collaborative sports betting tracker app for two brothers to track NFL Playoffs and Bowl Games with automated settlement and shared leaderboards.

## Features

✅ **Dual User Support** - Track bets for two users (brothers)  
✅ **Bet Types** - Support for Point Spreads and Over/Under totals  
✅ **Automated Settlement** - Integrates with The Odds API to automatically settle bets  
✅ **Vig/Juice Calculation** - Automatically applies 10% vig to losing bets  
✅ **Individual Dashboards** - See each user's performance separately  
✅ **Shared Leaderboard** - Running total comparison between both users  
✅ **Real-time Updates** - JSON-based storage (easily migratable to Supabase)  

## Installation

1. **Activate your virtual environment:**
   ```bash
   venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Run the app:**
   ```bash
   streamlit run bet_tracker.py
   ```

2. **Set up user names** in the sidebar

3. **Place bets** using the "Place Bet" tab

4. **Auto-settle bets** by clicking "⚖️ Auto-Settle Bets" in the sidebar (fetches scores from last 3 days)

5. **View leaderboard** to see running totals and performance

## How It Works

### The Juice (Vig)
- **Winning bets:** Profit = Stake
- **Losing bets:** Loss = Stake × 1.1 (10% vig applied)
- **Push bets:** Profit = 0 (stake returned)

### Bet Settlement
The app uses The Odds API to:
- Fetch final scores from completed games (last 3 days)
- Match bets to games using team name normalization
- Automatically calculate Win/Loss/Push based on:
  - **Spread bets:** Team score + spread vs opponent score
  - **Over/Under:** Total game score vs bet line

### Example
If User A bets $100 on Team A -3.5 and Team A wins by only 3 points:
- Result: **LOSS**
- Loss amount: **-$110** (stake × 1.1 for vig)

## Data Storage

Bets are stored in `bets_data.json` in the project directory. This can be easily migrated to Supabase or another database by updating the `load_bets()` and `save_bets()` functions.

## API Key

The app uses The Odds API with the provided key. The key is configured in the code. For production, consider moving it to environment variables or Streamlit secrets.

## Notes

- Game names should match API format (e.g., "Oklahoma vs Alabama")
- The app normalizes team names for matching, but exact matches work best
- Auto-settle checks games from the last 3 days
- All bets are persistent across app restarts

