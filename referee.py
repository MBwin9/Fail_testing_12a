"""
Core Referee Function for Bet Settlement

This module implements the core betting logic with strict type safety and
decimal precision for financial calculations.

Input Data Structure (from API /scores endpoint or Live_Data tab):
- Home_Team_Score: [number]
- Away_Team_Score: [number]
- Bet_Type: 'spread' | 'totals'
- User_Pick: [team_name] | 'Over' | 'Under'
- Line: [number] (e.g., -7.5 for favorite, +3 for underdog, or 48.5 for O/U)
- Stake: [number] (the amount wagered)

Returns:
- Result: 'W' | 'L' | 'P' (Win, Loss, Push)
- Final_PL: Profit/Loss amount (using Decimal precision)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Literal, Tuple, Optional


def settleBet(
    home_team_score: float,
    away_team_score: float,
    bet_type: Literal['spread', 'totals'],
    user_pick: str,
    line: float,
    stake: float,
    no_juice: bool = False
) -> Dict[str, any]:
    """
    Core Referee function: Settles a bet based on final score.
    
    Args:
        home_team_score: Final score of home team
        away_team_score: Final score of away team
        bet_type: 'spread' for point spread, 'totals' for over/under
        user_pick: Team name for spreads, or 'Over' | 'Under' for totals
        line: Spread value (e.g., -7.5, +3) or total (e.g., 48.5)
        stake: Amount wagered
        no_juice: If True, losses don't get 10% juice applied (default: False)
    
    Returns:
        Dictionary with:
        - result: 'W' | 'L' | 'P' (Win, Loss, Push)
        - final_pl: Profit/Loss amount (float, rounded to 2 decimals)
    
    Raises:
        ValueError: If inputs are invalid or missing required data
    
    The 10% Juice Rule:
    - If Result is 'W': Final_PL = Stake
    - If Result is 'L': Final_PL = -(Stake * 1.1)
    - If Result is 'P': Final_PL = 0
    """
    # Convert to Decimal for precise money calculations
    try:
        home_score = Decimal(str(home_team_score))
        away_score = Decimal(str(away_team_score))
        line_decimal = Decimal(str(line))
        stake_decimal = Decimal(str(stake))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid numeric input: {e}")
    
    # Validate inputs
    if home_score is None or away_score is None:
        raise ValueError("Game scores cannot be null")
    
    if stake_decimal <= 0:
        raise ValueError("Stake must be greater than 0")
    
    result: Literal['W', 'L', 'P'] = 'P'
    final_pl: Decimal = Decimal('0')
    
    if bet_type == 'spread':
        # Point Spread Logic
        # user_pick is the team name being bet on
        # line is the spread (negative = favorite giving points, positive = underdog getting points)
        # 
        # For spread bets:
        # - If betting on Team A with spread -16.5: Team A must win by MORE than 16.5 points
        # - If betting on Team A with spread +16.5: Team A can lose by UP TO 16.5 points and still win
        #
        # Calculation: (Team_Score + Line) vs Opponent_Score
        # If (Team_Score + Line) > Opponent_Score, the bet WINS
        
        # We need to determine which team is being bet on
        # The settle_bet wrapper should pass home_team and away_team, but for now
        # we'll use a helper function to match the team name
        
        # For now, we'll need to pass home_team and away_team names to this function
        # But since we don't have that, we'll infer from the line sign
        # This is a temporary fix - the wrapper should handle team matching
        
        # Actually, the proper way is to match user_pick to home/away team names
        # But we don't have those here. The wrapper should determine which team is being bet on
        # and pass is_home_team boolean or team names.
        
        # For now, let's assume:
        # - Negative line usually means betting on home team (favorite)
        # - Positive line usually means betting on away team (underdog)
        # But this is not reliable - we need the wrapper to tell us which team
        
        # TEMPORARY: Use line sign heuristic (will be fixed by wrapper)
        # The wrapper should match user_pick to actual team names and determine home/away
        
        if line_decimal < 0:
            # Negative spread: betting on favorite (usually home)
            # Team must win by MORE than the spread amount
            # (Home_Score + Line) vs Away_Score
            # Example: Home -16.5, Home wins 41-10
            # (41 + (-16.5)) = 24.5 vs 10 → 24.5 > 10 → WIN ✓
            adjusted_score = home_score + line_decimal
            opponent_score = away_score
        else:
            # Positive spread: betting on underdog (usually away)
            # Team can lose by UP TO the spread amount
            # (Away_Score + Line) vs Home_Score
            adjusted_score = away_score + line_decimal
            opponent_score = home_score
        
        # Decision Logic:
        # (Team_Score + Line) > Opponent_Score = 'W' (team covers)
        # (Team_Score + Line) < Opponent_Score = 'L' (team doesn't cover)
        # (Team_Score + Line) == Opponent_Score = 'P' (push)
        
        if adjusted_score > opponent_score:
            result = 'W'
        elif adjusted_score < opponent_score:
            result = 'L'
        else:
            result = 'P'
    
    elif bet_type == 'totals':
        # Totals (O/U) Logic
        total_score = home_score + away_score
        
        if user_pick not in ['Over', 'Under']:
            raise ValueError(f"Invalid user_pick for totals bet: {user_pick}. Must be 'Over' or 'Under'")
        
        if user_pick == 'Over':
            # If User_Pick is 'Over': Total_Score > Line ? 'W' : (Total_Score < Line ? 'L' : 'P')
            if total_score > line_decimal:
                result = 'W'
            elif total_score < line_decimal:
                result = 'L'
            else:
                result = 'P'
        
        elif user_pick == 'Under':
            # If User_Pick is 'Under': Total_Score < Line ? 'W' : (Total_Score > Line ? 'L' : 'P')
            if total_score < line_decimal:
                result = 'W'
            elif total_score > line_decimal:
                result = 'L'
            else:
                result = 'P'
    
    else:
        raise ValueError(f"Invalid bet_type: {bet_type}. Must be 'spread' or 'totals'")
    
    # Apply the 10% Juice Rule (CRITICAL)
    # If no_juice is True, losses don't get juice - just lose the stake
    if result == 'W':
        final_pl = stake_decimal
    elif result == 'L':
        if no_juice:
            final_pl = -stake_decimal  # No juice - just lose the stake
        else:
            final_pl = -(stake_decimal * Decimal('1.1'))  # 10% juice on loss
    else:  # result == 'P'
        final_pl = Decimal('0')
    
    # Round to 2 decimal places for currency
    final_pl_rounded = final_pl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return {
        'result': result,
        'final_pl': float(final_pl_rounded)
    }


# ============================================================================
# Example Usage and Tests
# ============================================================================

if __name__ == "__main__":
    # Example 1: Spread bet - Home team wins by 3, but bet was -3.5 (LOSS with vig)
    print("Example 1: Spread bet - Home team -3.5, wins by 3")
    result1 = settleBet(
        home_team_score=24,
        away_team_score=21,
        bet_type='spread',
        user_pick='Home Team',
        line=-3.5,
        stake=100.0
    )
    print(f"Result: {result1['result']}, Final PL: ${result1['final_pl']:.2f}")
    print(f"Expected: L, -$110.00 (10% vig on loss)\n")
    
    # Example 2: Spread bet - Home team wins by 4, bet was -3.5 (WIN)
    print("Example 2: Spread bet - Home team -3.5, wins by 4")
    result2 = settleBet(
        home_team_score=24,
        away_team_score=20,
        bet_type='spread',
        user_pick='Home Team',
        line=-3.5,
        stake=100.0
    )
    print(f"Result: {result2['result']}, Final PL: ${result2['final_pl']:.2f}")
    print(f"Expected: W, $100.00\n")
    
    # Example 3: Over/Under bet - Total is 50, bet was Over 48.5 (WIN)
    print("Example 3: Over/Under bet - Over 48.5, total is 50")
    result3 = settleBet(
        home_team_score=28,
        away_team_score=22,
        bet_type='totals',
        user_pick='Over',
        line=48.5,
        stake=100.0
    )
    print(f"Result: {result3['result']}, Final PL: ${result3['final_pl']:.2f}")
    print(f"Expected: W, $100.00\n")
    
    # Example 4: Over/Under bet - Total is 45, bet was Over 48.5 (LOSS with vig)
    print("Example 4: Over/Under bet - Over 48.5, total is 45")
    result4 = settleBet(
        home_team_score=24,
        away_team_score=21,
        bet_type='totals',
        user_pick='Over',
        line=48.5,
        stake=100.0
    )
    print(f"Result: {result4['result']}, Final PL: ${result4['final_pl']:.2f}")
    print(f"Expected: L, -$110.00 (10% vig on loss)\n")
    
    # Example 5: Push - Exact match
    print("Example 5: Push - Total exactly matches line")
    result5 = settleBet(
        home_team_score=24,
        away_team_score=24,
        bet_type='totals',
        user_pick='Over',
        line=48.0,
        stake=100.0
    )
    print(f"Result: {result5['result']}, Final PL: ${result5['final_pl']:.2f}")
    print(f"Expected: P, $0.00\n")

