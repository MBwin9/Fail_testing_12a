# Referee Function Implementation

## Overview

The core `settleBet` function implements the betting settlement logic with strict type safety and decimal precision for financial calculations.

## Core Function: `settleBet()`

**Location:** `referee.py`

### Input Data Structure

```python
settleBet(
    home_team_score: float,      # Final score of home team
    away_team_score: float,      # Final score of away team
    bet_type: 'spread' | 'totals',
    user_pick: str,              # Team name (spread) or 'Over'/'Under' (totals)
    line: float,                 # Spread value or total line
    stake: float,                # Amount wagered
    is_home_team: bool          # Required for spread bets
)
```

### Return Value

```python
{
    'result': 'W' | 'L' | 'P',   # Win, Loss, or Push
    'final_pl': float            # Profit/Loss (rounded to 2 decimals)
}
```

## Decision Logic

### A. Point Spread Logic

- **If User_Pick matches Home_Team:** `(Home_Score + Line) vs Away_Score`
- **If User_Pick matches Away_Team:** `(Away_Score + Line) vs Home_Score`

**Decision Rules:**
- `(Score + Line) > Opponent_Score` → **'W'** (Win)
- `(Score + Line) < Opponent_Score` → **'L'** (Loss)
- `(Score + Line) == Opponent_Score` → **'P'** (Push)

### B. Totals (O/U) Logic

- **Total_Score = Home_Score + Away_Score**

**For 'Over' bets:**
- `Total_Score > Line` → **'W'**
- `Total_Score < Line` → **'L'**
- `Total_Score == Line` → **'P'**

**For 'Under' bets:**
- `Total_Score < Line` → **'W'**
- `Total_Score > Line` → **'L'**
- `Total_Score == Line` → **'P'**

## The 10% Juice Rule (CRITICAL)

Financial settlement logic:

- **If Result is 'W':** `Final_PL = Stake`
- **If Result is 'L':** `Final_PL = -(Stake * 1.1)` ← **10% vig applied**
- **If Result is 'P':** `Final_PL = 0`

### Example

A $100 bet that loses:
- Loss = $100 × 1.1 = **-$110.00**

## Technical Implementation

### Decimal Precision

Uses Python's `Decimal` type to avoid floating-point errors in money calculations:

```python
from decimal import Decimal, ROUND_HALF_UP

stake_decimal = Decimal(str(stake))
final_pl = -(stake_decimal * Decimal('1.1'))
final_pl_rounded = final_pl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
```

### Error Handling

- Validates that scores are not null
- Validates stake > 0
- Validates bet_type is 'spread' or 'totals'
- Validates user_pick for totals bets ('Over' or 'Under')
- Requires `is_home_team` parameter for spread bets

## Integration

The `settleBet` function is integrated into `bet_tracker.py` via the `settle_bet()` wrapper function, which:

1. Extracts scores from API response (handles multiple formats)
2. Matches team names to determine home/away
3. Converts bet structure to `settleBet` parameters
4. Updates bet record with results

## Testing

Run `python referee.py` to see example test cases:

```bash
python referee.py
```

Example outputs:
- Spread bet losing by 0.5 points: **L, -$110.00** (10% vig)
- Spread bet winning: **W, $100.00**
- Over bet winning: **W, $100.00**
- Over bet losing: **L, -$110.00** (10% vig)
- Push (exact match): **P, $0.00**

## Success Criteria Verification

✅ **Example from requirements:**
- Bet: $100 on team at -3.5
- Result: Team wins by 3 (not covering the spread)
- Expected: **LOSS of $110** (stake × 1.1)

**Implementation confirms:** The function correctly calculates this scenario.

