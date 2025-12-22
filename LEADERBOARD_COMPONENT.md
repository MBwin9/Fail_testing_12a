# Leaderboard Component Documentation

## Overview

The Leaderboard component provides a comprehensive view of betting performance for both brothers, with real-time aggregation, visual comparisons, and detailed statistics.

## Features Implemented

### 1. Data Aggregation ✅

- **Fetches all bets** from the bets collection (stored in `bets_data.json`)
- **Groups by Bettor** (User A and User B)
- **Sums Final_PL** (Profit/Loss) for each brother
- **Calculates total Juice Paid** (10% of all losing bet stakes)
- **Identifies Current Leader** (brother with highest Net P/L)

### 2. UI/UX Components ✅

#### Season Standings Card
- Displays current leader at the top
- Shows who's ahead with their total profit
- Handles tie scenarios

#### Head-to-Head Comparison
- Visual progress bars showing relative performance
- Comprehensive comparison table with:
  - Net Profit/Loss
  - Record (W-L-P)
  - Win Rate
  - Total Bets
  - Pending Bets
  - Juice Paid

#### Individual Performance Cards
- Side-by-side display for each brother
- Color-coded Net P/L (green for positive, red for negative)
- Detailed metrics:
  - Wins, Losses, Pushes
  - Win Rate
  - Total and Pending bets
  - Juice Paid (displayed as cost)

#### Recent Activity
- Last 5 settled bets
- Color-coded results (green W, red L, gray P)
- Color-coded profit/loss
- Shows user, game, bet details, stake, result, and settlement date

### 3. Logic Implementation ✅

#### Push Handling (CRITICAL)
- **Pushes are treated as "No Action"**
- Profit/Loss = 0 for pushes
- **Win Rate calculation excludes pushes**: `Win Rate = Wins / (Wins + Losses)`
- Pushes are counted separately but don't affect win percentage

#### Juice Calculation (CRITICAL)
- **10% penalty on all losses**
- Formula: `Juice Paid = Sum(Stake × 0.1) for all Losses`
- Displayed as a negative cost in the UI
- Correctly reflected in Final_PL calculations

### 4. Component Interaction ✅

#### Refresh Button
- Located in the Leaderboard tab header
- Labeled "🔄 Refresh & Re-Settle"
- Functionality:
  1. Fetches latest scores from The Odds API (last 3 days)
  2. Re-runs settlement logic on all unsettled bets
  3. Saves updated bets to storage
  4. Refreshes the UI with new data

## Technical Details

### Functions

#### `calculate_user_stats(bets, user)`
- Aggregates all statistics for a single user
- Returns dictionary with:
  - `total_bets`: Total number of bets
  - `wins`, `losses`, `pushes`: Count of each result type
  - `pending`: Number of unsettled bets
  - `total_profit`: Sum of all Final_PL values
  - `juice_paid`: Total juice paid (10% of losing stakes)
  - `win_rate`: Win percentage (excludes pushes)
  - `settled_bets`: List of all settled bets

#### `get_recent_activity(bets, limit=5)`
- Retrieves the most recent settled bets
- Sorted by `settled_at` timestamp (most recent first)
- Returns top N bets

### Color Coding

- **Green**: Positive values, wins, profitable bets
- **Red**: Negative values, losses, costs (juice)
- **Gray**: Pushes (neutral)

### Mobile Responsiveness

- Custom CSS media queries for screens < 768px
- Streamlit's built-in responsive layout
- Columns automatically stack on mobile
- Font sizes adjust for smaller screens

## Data Flow

1. **Load Bets**: `initialize_data()` → `load_bets()` → `st.session_state.bets`
2. **Calculate Stats**: `calculate_user_stats()` for each user
3. **Display**: Render components with aggregated data
4. **Refresh**: User clicks refresh → Fetch scores → Auto-settle → Save → Re-render

## Example Output

### Season Standings
```
🏆 Current Leader
John is leading with +$250.00
```

### Head-to-Head Comparison
```
Metric              | John    | Mike
Net Profit/Loss     | +$250.00| -$110.00
Record (W-L-P)      | 5-2-1   | 3-4-0
Win Rate            | 71.4%   | 42.9%
Total Bets          | 8       | 7
Pending Bets        | 2       | 1
Juice Paid          | -$20.00 | -$40.00
```

### Recent Activity
```
John | Oklahoma vs Alabama
Oklahoma -3.5 | Stake: $100.00
✓ W  | +$100.00
Settled: 2024-01-15 14:30
```

## Success Criteria Verification

✅ **Pushes treated as "No Action"**: Win rate calculation excludes pushes  
✅ **Juice correctly calculated**: 10% of all losing stakes summed  
✅ **Current leader identified**: Highest Net P/L displayed  
✅ **Color coding**: Green for positive, red for negative  
✅ **Recent activity**: Last 5 settled bets shown  
✅ **Refresh functionality**: Re-fetches and re-settles bets  
✅ **Mobile responsive**: CSS media queries and Streamlit layout

## Future Enhancements

- Charts/graphs for profit trends over time
- Export functionality for records
- Filter by date range
- Betting streak tracking
- Head-to-head matchup history

