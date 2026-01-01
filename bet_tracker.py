import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional, Tuple, Literal
from decimal import Decimal, ROUND_HALF_UP
from referee import settleBet

# Configuration
# Try to get API key from Streamlit secrets (for cloud deployment), otherwise use default
try:
    if hasattr(st, 'secrets') and 'API_KEY' in st.secrets:
        API_KEY = st.secrets["API_KEY"]
    else:
        API_KEY = "5d01a63b3ba3428b2b1b677305ef7c3b"
except:
    API_KEY = "5d01a63b3ba3428b2b1b677305ef7c3b"
DATA_FILE = "bets_data.json"
SPORT_MAP = {
    "NFL": "americanfootball_nfl",
    "NCAAF": "americanfootball_ncaaf"
}

# Initialize session state
if 'bets' not in st.session_state:
    st.session_state.bets = []
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'users' not in st.session_state:
    st.session_state.users = ["Michael", "Tim", "User C"]
if 'user_names' not in st.session_state:
    # User name mappings (for backward compatibility and User C)
    st.session_state.user_names = {
        "Michael": "Michael",
        "Tim": "Tim",
        "User C": ""
    }

# ============================================================================
# DATA PERSISTENCE
# ============================================================================

def load_bets() -> List[Dict]:
    """Load bets from storage (Supabase if available, otherwise JSON file)"""
    # Try Supabase first (for cloud deployment)
    try:
        if hasattr(st, 'secrets') and 'SUPABASE_URL' in st.secrets:
            return load_bets_from_supabase()
    except Exception as e:
        pass
    
    # Fallback to local JSON file
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_bets(bets: List[Dict]):
    """Save bets to storage (Supabase if available, otherwise JSON file)"""
    # Safety check: Don't save empty data
    if not bets or len(bets) == 0:
        st.warning("⚠️ Attempted to save empty bets list. Data not saved to prevent data loss.")
        return
    
    # Try Supabase first (for cloud deployment)
    try:
        if hasattr(st, 'secrets') and 'SUPABASE_URL' in st.secrets:
            save_bets_to_supabase(bets)
            return
    except Exception as e:
        st.warning(f"Could not save to Supabase: {e}. Saving to local file instead.")
    
    # Fallback to local JSON file
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(bets, f, indent=2)
    except Exception as e:
        st.error(f"Could not save bets: {e}")

def load_bets_from_supabase() -> List[Dict]:
    """Load bets from Supabase"""
    try:
        from supabase import create_client, Client
        
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Fetch all bets
        response = supabase.table("bets").select("*").execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error loading from Supabase: {e}")
        return []

def save_bets_to_supabase(bets: List[Dict]):
    """Save bets to Supabase"""
    try:
        from supabase import create_client, Client
        
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Safety check: Don't delete all data if bets list is empty
        if not bets or len(bets) == 0:
            st.warning("⚠️ Attempted to save empty bets list. Data not saved to prevent data loss.")
            return
        
        # Delete all existing bets
        supabase.table("bets").delete().neq("id", -1).execute()
        
        # Insert all bets
        # Supabase expects a list of dicts
        supabase.table("bets").insert(bets).execute()
    except Exception as e:
        raise Exception(f"Error saving to Supabase: {e}")

def initialize_data():
    """Initialize session state with saved data"""
    # Only load if we haven't loaded data yet in this session
    if not st.session_state.data_loaded:
        loaded_bets = load_bets()
        if loaded_bets:
            st.session_state.bets = loaded_bets
        st.session_state.data_loaded = True

# ============================================================================
# API FUNCTIONS
# ============================================================================

@st.cache_data(ttl=timedelta(minutes=15))
def fetch_odds(api_key: str, sport_key: str) -> Optional[List[Dict]]:
    """Fetch current odds from The Odds API"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching odds: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching odds: {str(e)}")
        return None

@st.cache_data(ttl=timedelta(minutes=15))
def fetch_scores(api_key: str, sport_key: str, days: int = 3) -> Optional[List[Dict]]:
    """Fetch final scores from The Odds API for the last N days"""
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores"
    params = {
        "apiKey": api_key,
        "daysFrom": days
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Error fetching scores: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching scores: {str(e)}")
        return None

def normalize_team_name(name: str) -> str:
    """Normalize team names for matching"""
    # Remove common suffixes and normalize
    name = name.strip()
    # Remove city prefixes if needed, keep team name
    # This is a basic implementation - may need refinement
    return name

def find_matching_game(bet_game: str, scores: List[Dict]) -> Optional[Dict]:
    """Find matching game in scores data"""
    # Handle different game name formats
    if " vs " in bet_game:
        bet_home, bet_away = bet_game.split(" vs ")
    elif " @ " in bet_game:
        bet_away, bet_home = bet_game.split(" @ ")
    else:
        # Try to parse other formats
        parts = bet_game.split()
        if len(parts) >= 2:
            bet_away = parts[0]
            bet_home = parts[-1]
        else:
            return None
    
    bet_home = normalize_team_name(bet_home)
    bet_away = normalize_team_name(bet_away)
    
    for score in scores:
        # Check if game is completed
        completed = score.get('completed', False) or score.get('scores') is not None
        
        if completed:
            home = normalize_team_name(score.get('home_team', ''))
            away = normalize_team_name(score.get('away_team', ''))
            
            # More flexible matching
            def teams_match(team1: str, team2: str) -> bool:
                t1 = team1.lower().strip()
                t2 = team2.lower().strip()
                # Exact match
                if t1 == t2:
                    return True
                # Substring match
                if t1 in t2 or t2 in t1:
                    return True
                # Word-based match (for team names with multiple words)
                words1 = set(w for w in t1.split() if len(w) > 3)
                words2 = set(w for w in t2.split() if len(w) > 3)
                if words1 and words2 and (words1 & words2):
                    return True
                return False
            
            # Check both directions
            if teams_match(bet_home, home) and teams_match(bet_away, away):
                return score
            # Reverse check
            if teams_match(bet_home, away) and teams_match(bet_away, home):
                return score
    
    return None

# ============================================================================
# REFEREE FUNCTION - BET SETTLEMENT
# ============================================================================
# Note: settleBet() is imported from referee.py

def settle_bet(bet: Dict, game_score: Dict) -> Dict:
    """
    Wrapper function that extracts data from bet and game_score structures
    and calls the core settleBet function.
    
    This function handles:
    - Extracting scores from API response
    - Matching team names
    - Converting bet structure to settleBet parameters
    """
    # Extract scores - handle different API response formats
    scores_data = game_score.get('scores', [])
    if isinstance(scores_data, list) and len(scores_data) >= 2:
        home_score = scores_data[0].get('score', 0) if isinstance(scores_data[0], dict) else 0
        away_score = scores_data[1].get('score', 0) if isinstance(scores_data[1], dict) else 0
    else:
        # Try alternative format
        home_score = game_score.get('home_score', game_score.get('scores', {}).get('home', 0))
        away_score = game_score.get('away_score', game_score.get('scores', {}).get('away', 0))
    
    # Validate scores
    if home_score is None or away_score is None:
        raise ValueError("Game scores are missing or null")
    
    # Get actual teams from score
    score_home = game_score.get('home_team', '')
    score_away = game_score.get('away_team', '')
    
    # Extract bet data
    bet_type_str = bet.get('bet_type', '').lower()
    if bet_type_str == 'spread':
        bet_type = 'spread'
    elif bet_type_str == 'over/under':
        bet_type = 'totals'
    else:
        raise ValueError(f"Invalid bet_type: {bet.get('bet_type')}")
    
    stake = bet.get('stake', 0)
    user_pick = bet.get('team', '') if bet_type == 'spread' else bet.get('direction', '')
    line = bet.get('spread', 0) if bet_type == 'spread' else bet.get('total', 0)
    
    # Get no_juice flag from bet
    no_juice = bet.get('no_juice', False)
    
    # For spread bets, we need to determine which team is being bet on
    # and ensure the scores are aligned correctly
    if bet_type == 'spread':
        # Normalize team names for matching (case-insensitive, remove extra spaces)
        def normalize_team_name(name):
            return name.strip().lower().replace(' ', '')
        
        user_pick_normalized = normalize_team_name(user_pick)
        home_normalized = normalize_team_name(score_home)
        away_normalized = normalize_team_name(score_away)
        
        # Determine which team is being bet on
        betting_on_home = False
        if user_pick_normalized == home_normalized:
            betting_on_home = True
        elif user_pick_normalized == away_normalized:
            betting_on_home = False
        else:
            # Team name doesn't match exactly - try partial matching
            if user_pick_normalized in home_normalized or home_normalized in user_pick_normalized:
                betting_on_home = True
            elif user_pick_normalized in away_normalized or away_normalized in user_pick_normalized:
                betting_on_home = False
            else:
                # Fallback: use line sign as heuristic
                betting_on_home = (line < 0)
        
        # Now we need to ensure home_score and away_score are correct
        # If betting on home team, use home_score + line vs away_score
        # If betting on away team, use away_score + line vs home_score
        # But settleBet expects home_team_score and away_team_score in order
        # So we need to pass them correctly
        
        # The settleBet function will use the line sign, but we've already determined
        # which team is being bet on. We need to pass this information.
        # For now, let's ensure the scores are in the right order based on which team is being bet on
        
        # Actually, settleBet uses line sign to determine which team
        # But we know which team from user_pick. Let's adjust the logic:
        # If betting on home with -16.5: home_score + (-16.5) vs away_score
        # If betting on away with +16.5: away_score + 16.5 vs home_score
        
        # We'll swap scores if needed to make the logic work
        # But actually, the better approach is to fix settleBet to accept which team is being bet on
        
        # For now, let's ensure the line sign matches the team being bet on
        # If betting on home, line should typically be negative
        # If betting on away, line should typically be positive
        # But this isn't always true, so we need to handle it properly
        
        # The correct approach: Calculate directly
        if betting_on_home:
            # Betting on home team
            # Adjusted score = home_score + line
            # Compare to away_score
            adjusted_score = home_score + line
            opponent_score = away_score
        else:
            # Betting on away team
            # Adjusted score = away_score + line
            # Compare to home_score
            adjusted_score = away_score + line
            opponent_score = home_score
        
        # Now call settleBet, but we need to ensure it uses the right logic
        # Since settleBet uses line sign, we might need to swap scores or adjust
        # Actually, let's just calculate the result here and pass it through
        
        if adjusted_score > opponent_score:
            result = 'W'
        elif adjusted_score < opponent_score:
            result = 'L'
        else:
            result = 'P'
        
        # Calculate P/L using Decimal for precision
        from decimal import Decimal, ROUND_HALF_UP
        stake_decimal = Decimal(str(stake))
        
        if result == 'W':
            final_pl = float(stake_decimal)
        elif result == 'L':
            if no_juice:
                final_pl = float(-stake_decimal)
            else:
                final_pl = float(-(stake_decimal * Decimal('1.1')))
        else:
            final_pl = 0.0
        
        # Round to 2 decimal places
        final_pl = round(final_pl, 2)
        
        # Update bet with results
        updated_bet = bet.copy()
        updated_bet['result'] = result
        updated_bet['profit'] = round(final_pl, 2)
        updated_bet['payout'] = stake if result == 'W' else (stake if result == 'P' else 0)
        updated_bet['settled'] = True
        updated_bet['settled_at'] = datetime.now().isoformat()
        updated_bet['final_score'] = f"{score_home} {home_score} - {away_score} {score_away}"
        
        return updated_bet
    
    # For totals bets, use the original logic
    try:
        settlement = settleBet(
            home_team_score=home_score,
            away_team_score=away_score,
            bet_type=bet_type,
            user_pick=user_pick,
            line=line,
            stake=stake,
            no_juice=no_juice
        )
        result = settlement['result']
        final_pl = settlement['final_pl']
    except Exception as e:
        st.error(f"Error settling bet: {str(e)}")
        raise
    
    # Update bet with results
    updated_bet = bet.copy()
    updated_bet['result'] = result
    updated_bet['profit'] = final_pl
    updated_bet['payout'] = stake if result == 'W' else (stake if result == 'P' else 0)
    updated_bet['settled'] = True
    updated_bet['settled_at'] = datetime.now().isoformat()
    updated_bet['final_score'] = f"{score_home} {home_score} - {away_score} {score_away}"
    
    return updated_bet

def auto_settle_bets(bets: List[Dict], scores: List[Dict]) -> List[Dict]:
    """Automatically settle all unsettled bets that have completed games"""
    updated_bets = []
    for bet in bets:
        if bet.get('settled', False):
            updated_bets.append(bet)
            continue
        
        # Find matching game
        game_score = find_matching_game(bet['game'], scores)
        if game_score and game_score.get('completed', False):
            settled_bet = settle_bet(bet, game_score)
            updated_bets.append(settled_bet)
        else:
            updated_bets.append(bet)
    
    return updated_bets

# ============================================================================
# UI COMPONENTS
# ============================================================================

def format_currency(amount: float) -> str:
    """Format currency with proper sign"""
    sign = '+' if amount >= 0 else ''
    return f"{sign}${amount:,.2f}"

def calculate_user_stats(bets: List[Dict], user: str) -> Dict:
    """
    Calculate comprehensive statistics for a user.
    Pushes are treated as "No Action" - not counted in win rate.
    """
    user_bets = [b for b in bets if b.get('user') == user]
    settled_bets = [b for b in user_bets if b.get('settled', False)]
    
    total_bets = len(user_bets)
    wins = len([b for b in settled_bets if b.get('result') == 'W'])
    losses = len([b for b in settled_bets if b.get('result') == 'L'])
    pushes = len([b for b in settled_bets if b.get('result') == 'P'])
    pending = len([b for b in user_bets if not b.get('settled', False)])
    
    # Total Profit/Loss (Final_PL)
    total_profit = sum([b.get('profit', 0) for b in settled_bets])
    
    # Calculate Juice Paid (10% of all losing bet stakes, excluding no_juice bets)
    juice_paid = sum([
        b.get('stake', 0) * 0.1  # 10% of stake on each loss (only if not no_juice)
        for b in settled_bets 
        if b.get('result') == 'L' and not b.get('no_juice', False)
    ])
    
    # Win rate: Only count W and L (pushes are "No Action")
    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    
    return {
        'total_bets': total_bets,
        'wins': wins,
        'losses': losses,
        'pushes': pushes,
        'pending': pending,
        'total_profit': total_profit,
        'juice_paid': juice_paid,
        'win_rate': win_rate,
        'settled_bets': settled_bets
    }

def get_recent_activity(bets: List[Dict], limit: int = 5) -> List[Dict]:
    """Get the last N settled bets, sorted by settlement time"""
    settled = [b for b in bets if b.get('settled', False)]
    # Sort by settled_at (most recent first)
    settled.sort(key=lambda x: x.get('settled_at', ''), reverse=True)
    return settled[:limit]

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    st.set_page_config(
        page_title="Brothers Bet Tracker", 
        page_icon="🏈", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Simple password protection
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🔒 Access Required")
        password = st.text_input("Enter password:", type="password", key="password_input")
        
        # Set your password here (change this!)
        correct_password = "bet2024"  # CHANGE THIS TO YOUR PASSWORD
        
        if st.button("Login"):
            if password == correct_password:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
        return
    
    # Add custom CSS for mobile responsiveness and styling
    st.markdown("""
    <style>
    /* Mobile responsive adjustments */
    @media (max-width: 768px) {
        .stMetric {
            padding: 0.5rem;
        }
        h2, h3 {
            font-size: 1.2rem;
        }
    }
    
    /* Color coding for positive/negative values */
    .positive-value {
        color: #00cc00;
        font-weight: bold;
    }
    .negative-value {
        color: #ff4444;
        font-weight: bold;
    }
    
    /* Card styling */
    .bet-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize data
    initialize_data()
    
    # Header
    st.title("🏈 Brothers Bet Tracker")
    st.markdown("**Track NFL Playoffs and Bowl Games - Shared Leaderboard**")
    
    # Sidebar
    st.sidebar.header("⚙️ Settings")
    
    # User names (hardcoded)
    st.sidebar.subheader("User Names")
    st.sidebar.write("**Michael**")
    st.sidebar.write("**Tim**")
    user_c_name = st.sidebar.text_input("User C Name", value=st.session_state.user_names.get("User C", ""), key="user_c")
    
    if user_c_name:
        st.session_state.user_names["User C"] = user_c_name
        # Update users list if User C name is set
        if user_c_name and "User C" in st.session_state.users:
            st.session_state.users = ["Michael", "Tim", user_c_name]
            st.session_state.user_names[user_c_name] = user_c_name
    
    # League selection
    league = st.sidebar.selectbox("League", ["NFL", "NCAAF"], key="league")
    sport_key = SPORT_MAP[league]
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Auto-settle bets
    if st.sidebar.button("⚖️ Auto-Settle Bets"):
        scores = fetch_scores(API_KEY, sport_key, days=3)
        if scores:
            st.session_state.bets = auto_settle_bets(st.session_state.bets, scores)
            save_bets(st.session_state.bets)
            st.sidebar.success("Bets settled!")
            st.rerun()
        else:
            st.sidebar.error("Could not fetch scores")
    
    # Main tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Leaderboard", "➕ Place Bet", "📋 All Bets", "🎮 Games & Odds", "💰 Danny"])
    
    # ============================================================================
    # TAB 1: LEADERBOARD
    # ============================================================================
    with tab1:
        # Header with refresh button
        col_header1, col_header2 = st.columns([3, 1])
        with col_header1:
            st.header("📊 Season Standings")
        with col_header2:
            if st.button("🔄 Refresh & Re-Settle", use_container_width=True, type="primary"):
                scores = fetch_scores(API_KEY, sport_key, days=3)
                if scores:
                    st.session_state.bets = auto_settle_bets(st.session_state.bets, scores)
                    save_bets(st.session_state.bets)
                    st.success("✅ Bets refreshed and re-settled!")
                    st.rerun()
                else:
                    st.error("Could not fetch scores")
        
        # Calculate stats for all users
        user_a_stats = calculate_user_stats(st.session_state.bets, "Michael")
        user_b_stats = calculate_user_stats(st.session_state.bets, "Tim")
        user_c_stats = calculate_user_stats(st.session_state.bets, "User C")
        
        user_a_display = "Michael"
        user_b_display = "Tim"
        user_c_display = st.session_state.user_names.get("User C", "User C")
        
        # Determine current leader
        all_profits = {
            user_a_display: user_a_stats['total_profit'],
            user_b_display: user_b_stats['total_profit'],
            user_c_display: user_c_stats['total_profit']
        }
        leader = max(all_profits, key=all_profits.get) if all_profits else None
        leader_profit = all_profits[leader] if leader else 0
        
        # ========================================================================
        # SEASON STANDINGS CARD
        # ========================================================================
        st.markdown("### 🏆 Current Leader")
        if leader and leader_profit > 0:
            st.success(f"**{leader}** is leading with {format_currency(leader_profit)}")
        elif leader and leader_profit == 0:
            # Check for ties
            max_profit = max(all_profits.values())
            leaders = [k for k, v in all_profits.items() if v == max_profit]
            if len(leaders) > 1:
                st.info(f"🤝 **It's a tie!** {', '.join(leaders)} are tied.")
            else:
                st.info(f"**{leader}** is leading with {format_currency(leader_profit)}")
        else:
            st.info("No bets placed yet.")
        
        st.divider()
        
        # ========================================================================
        # HEAD-TO-HEAD COMPARISON
        # ========================================================================
        st.markdown("### 📊 Head-to-Head Comparison")
        
        # Visual comparison bar for Net P/L
        max_profit = max(abs(user_a_stats['total_profit']), abs(user_b_stats['total_profit']), abs(user_c_stats['total_profit']), 1)
        col_comp1, col_comp2, col_comp3 = st.columns(3)
        
        with col_comp1:
            profit_a = user_a_stats['total_profit']
            # Convert to 0-1 range for progress bar
            bar_width_a = abs(profit_a / max_profit) if max_profit > 0 else 0
            bar_width_a = max(0.0, min(1.0, bar_width_a))
            st.markdown(f"**{user_a_display}**")
            st.progress(bar_width_a, text=f"{format_currency(profit_a)}")
        
        with col_comp2:
            profit_b = user_b_stats['total_profit']
            # Convert to 0-1 range for progress bar
            bar_width_b = abs(profit_b / max_profit) if max_profit > 0 else 0
            bar_width_b = max(0.0, min(1.0, bar_width_b))
            st.markdown(f"**{user_b_display}**")
            st.progress(bar_width_b, text=f"{format_currency(profit_b)}")
        
        with col_comp3:
            profit_c = user_c_stats['total_profit']
            # Convert to 0-1 range for progress bar
            bar_width_c = abs(profit_c / max_profit) if max_profit > 0 else 0
            bar_width_c = max(0.0, min(1.0, bar_width_c))
            st.markdown(f"**{user_c_display}**")
            st.progress(bar_width_c, text=f"{format_currency(profit_c)}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Create comparison table
        comparison_data = {
            'Metric': [
                'Net Profit/Loss',
                'Record (W-L-P)',
                'Win Rate',
                'Total Bets',
                'Pending Bets',
                'Juice Paid'
            ],
            user_a_display: [
                format_currency(user_a_stats['total_profit']),
                f"{user_a_stats['wins']}-{user_a_stats['losses']}-{user_a_stats['pushes']}",
                f"{user_a_stats['win_rate']:.1f}%",
                str(user_a_stats['total_bets']),
                str(user_a_stats['pending']),
                format_currency(-user_a_stats['juice_paid']) if user_a_stats['juice_paid'] > 0 else "$0.00"
            ],
            user_b_display: [
                format_currency(user_b_stats['total_profit']),
                f"{user_b_stats['wins']}-{user_b_stats['losses']}-{user_b_stats['pushes']}",
                f"{user_b_stats['win_rate']:.1f}%",
                str(user_b_stats['total_bets']),
                str(user_b_stats['pending']),
                format_currency(-user_b_stats['juice_paid']) if user_b_stats['juice_paid'] > 0 else "$0.00"
            ],
            user_c_display: [
                format_currency(user_c_stats['total_profit']),
                f"{user_c_stats['wins']}-{user_c_stats['losses']}-{user_c_stats['pushes']}",
                f"{user_c_stats['win_rate']:.1f}%",
                str(user_c_stats['total_bets']),
                str(user_c_stats['pending']),
                format_currency(-user_c_stats['juice_paid']) if user_c_stats['juice_paid'] > 0 else "$0.00"
            ]
        }
        
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, width='stretch', hide_index=True)
        
        st.divider()
        
        # ========================================================================
        # INDIVIDUAL STATS CARDS
        # ========================================================================
        st.markdown("### 👥 Individual Performance")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Michael Card
            st.markdown(f"#### 👤 {user_a_display}")
            
            # Net P/L with color coding
            profit_a = user_a_stats['total_profit']
            profit_color = "green" if profit_a >= 0 else "red"
            st.markdown(
                f"<h2 style='color: {profit_color};'>Net P/L: {format_currency(profit_a)}</h2>",
                unsafe_allow_html=True
            )
            
            # Metrics
            col1a, col1b = st.columns(2)
            with col1a:
                st.metric("Wins", user_a_stats['wins'])
                st.metric("Losses", user_a_stats['losses'])
            with col1b:
                st.metric("Pushes", user_a_stats['pushes'])
                st.metric("Win Rate", f"{user_a_stats['win_rate']:.1f}%")
            
            # Additional stats
            st.markdown("---")
            st.write(f"**Total Bets:** {user_a_stats['total_bets']}")
            st.write(f"**Pending:** {user_a_stats['pending']}")
            
            # Juice paid (displayed as negative cost)
            juice_a = user_a_stats['juice_paid']
            if juice_a > 0:
                st.markdown(f"**Juice Paid:** <span style='color: red;'>-{format_currency(juice_a)}</span>", unsafe_allow_html=True)
        
        with col2:
            # Tim Card
            st.markdown(f"#### 👤 {user_b_display}")
            
            # Net P/L with color coding
            profit_b = user_b_stats['total_profit']
            profit_color = "green" if profit_b >= 0 else "red"
            st.markdown(
                f"<h2 style='color: {profit_color};'>Net P/L: {format_currency(profit_b)}</h2>",
                unsafe_allow_html=True
            )
            
            # Metrics
            col2a, col2b = st.columns(2)
            with col2a:
                st.metric("Wins", user_b_stats['wins'])
                st.metric("Losses", user_b_stats['losses'])
            with col2b:
                st.metric("Pushes", user_b_stats['pushes'])
                st.metric("Win Rate", f"{user_b_stats['win_rate']:.1f}%")
            
            # Additional stats
            st.markdown("---")
            st.write(f"**Total Bets:** {user_b_stats['total_bets']}")
            st.write(f"**Pending:** {user_b_stats['pending']}")
            
            # Juice paid (displayed as negative cost)
            juice_b = user_b_stats['juice_paid']
            if juice_b > 0:
                st.markdown(f"**Juice Paid:** <span style='color: red;'>-{format_currency(juice_b)}</span>", unsafe_allow_html=True)
        
        with col3:
            # User C Card
            st.markdown(f"#### 👤 {user_c_display}")
            
            # Net P/L with color coding
            profit_c = user_c_stats['total_profit']
            profit_color = "green" if profit_c >= 0 else "red"
            st.markdown(
                f"<h2 style='color: {profit_color};'>Net P/L: {format_currency(profit_c)}</h2>",
                unsafe_allow_html=True
            )
            
            # Metrics
            col3a, col3b = st.columns(2)
            with col3a:
                st.metric("Wins", user_c_stats['wins'])
                st.metric("Losses", user_c_stats['losses'])
            with col3b:
                st.metric("Pushes", user_c_stats['pushes'])
                st.metric("Win Rate", f"{user_c_stats['win_rate']:.1f}%")
            
            # Additional stats
            st.markdown("---")
            st.write(f"**Total Bets:** {user_c_stats['total_bets']}")
            st.write(f"**Pending:** {user_c_stats['pending']}")
            
            # Juice paid (displayed as negative cost)
            juice_c = user_c_stats['juice_paid']
            if juice_c > 0:
                st.markdown(f"**Juice Paid:** <span style='color: red;'>-{format_currency(juice_c)}</span>", unsafe_allow_html=True)
        
        st.divider()
        
        # ========================================================================
        # RECENT ACTIVITY
        # ========================================================================
        st.markdown("### 📋 Recent Activity")
        st.caption("Last 5 settled bets")
        
        recent_bets = get_recent_activity(st.session_state.bets, limit=5)
        
        if recent_bets:
            # Display each recent bet as a card
            for bet in recent_bets:
                user_display = st.session_state.user_names.get(bet.get('user', ''), bet.get('user', ''))
                
                if bet['bet_type'] == "Spread":
                    bet_desc = f"{bet.get('team', '')} {bet.get('spread', 0):+.1f}"
                else:
                    bet_desc = f"{bet.get('direction', '')} {bet.get('total', 0)}"
                
                result = bet.get('result', '-')
                profit = bet.get('profit', 0)
                stake = bet.get('stake', 0)
                
                # Create a card-like display
                with st.container():
                    col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
                    
                    with col_act1:
                        st.write(f"**{user_display}** | {bet.get('game', '')}")
                        st.caption(f"{bet_desc} | Stake: ${stake:,.2f}")
                    
                    with col_act2:
                        # Result with color
                        if result == 'W':
                            st.markdown(f"<span style='color: green; font-weight: bold; font-size: 18px;'>✓ W</span>", unsafe_allow_html=True)
                        elif result == 'L':
                            st.markdown(f"<span style='color: red; font-weight: bold; font-size: 18px;'>✗ L</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<span style='color: gray; font-weight: bold; font-size: 18px;'>— P</span>", unsafe_allow_html=True)
                    
                    with col_act3:
                        # Profit with color
                        profit_color = "green" if profit >= 0 else "red"
                        st.markdown(
                            f"<span style='color: {profit_color}; font-weight: bold; font-size: 18px;'>{format_currency(profit)}</span>",
                            unsafe_allow_html=True
                        )
                    
                    st.caption(f"Settled: {bet.get('settled_at', '')[:16] if bet.get('settled_at') else 'N/A'}")
                    st.divider()
        else:
            st.info("No settled bets yet. Place bets and they'll appear here once settled.")
    
    # ============================================================================
    # TAB 2: PLACE BET
    # ============================================================================
    with tab2:
        st.header("➕ Place New Bet")
        
        # Hard-coded Past Games Section
        with st.expander("📋 Past Games - Quick Add with Final Scores", expanded=True):
            st.markdown("**Pre-configured past games with final scores. Just add your bets!**")
            
            past_games = [
                {
                    'game': 'Tulane vs Ole Miss',
                    'team1': 'Tulane',
                    'team1_score': 10,
                    'team2': 'Ole Miss',
                    'team2_score': 41
                },
                {
                    'game': 'Jame Madison vs Oregon',
                    'team1': 'Jame Madison',
                    'team1_score': 34,
                    'team2': 'Oregon',
                    'team2_score': 51
                },
                {
                    'game': 'Miami vs TX AM',
                    'team1': 'Miami',
                    'team1_score': 10,
                    'team2': 'TX AM',
                    'team2_score': 3
                },
                {
                    'game': 'Alabama vs Oklahoma',
                    'team1': 'Alabama',
                    'team1_score': 34,
                    'team2': 'Oklahoma',
                    'team2_score': 24
                }
            ]
            
            for game_data in past_games:
                with st.form(f"past_game_{game_data['game'].replace(' ', '_')}", clear_on_submit=True):
                    st.markdown(f"**{game_data['game']}** - Final: {game_data['team1']} {game_data['team1_score']}, {game_data['team2']} {game_data['team2_score']}")
                    
                    col_past1, col_past2 = st.columns(2)
                    
                    with col_past1:
                        past_user = st.selectbox("User", ["Michael", "Tim", "User C"], key=f"past_user_{game_data['game']}")
                        past_bet_type = st.selectbox("Bet Type", ["Spread", "Over/Under"], key=f"past_type_{game_data['game']}")
                        past_stake = st.number_input("Stake ($)", min_value=1.0, value=50.0, step=1.0, key=f"past_stake_{game_data['game']}")
                        past_no_juice = st.checkbox("No Juice", value=False, key=f"past_no_juice_{game_data['game']}")
                    
                    with col_past2:
                        if past_bet_type == "Spread":
                            past_team = st.selectbox("Team", [game_data['team1'], game_data['team2']], key=f"past_team_{game_data['game']}")
                            past_spread = st.number_input("Spread", value=0.0, step=0.5, key=f"past_spread_{game_data['game']}")
                            past_total = None
                            past_direction = None
                        else:
                            past_total = st.number_input("Total", min_value=0.0, value=50.0, step=0.5, key=f"past_total_{game_data['game']}")
                            past_direction = st.selectbox("Direction", ["Over", "Under"], key=f"past_dir_{game_data['game']}")
                            past_team = None
                            past_spread = None
                    
                    past_submitted = st.form_submit_button(f"Add Bet for {game_data['game']}", type="primary", use_container_width=True)
                    
                    if past_submitted:
                        if past_bet_type == "Spread" and not past_team:
                            st.error("Please select a team for spread bets")
                        else:
                            # Create bet
                            new_past_bet = {
                                'id': len(st.session_state.bets) + 1,
                                'user': past_user,
                                'game': game_data['game'],
                                'bet_type': past_bet_type,
                                'stake': past_stake,
                                'team': past_team,
                                'spread': past_spread,
                                'total': past_total,
                                'direction': past_direction,
                                'no_juice': past_no_juice,
                                'result': None,
                                'settled': False,
                                'profit': 0,
                                'payout': 0,
                                'created_at': datetime.now().isoformat(),
                                'settled_at': None,
                                'final_score': None
                            }
                            
                            # Create game_score for immediate settlement
                            past_game_score = {
                                'home_team': game_data['team1'],
                                'away_team': game_data['team2'],
                                'scores': [
                                    {'score': game_data['team1_score']},
                                    {'score': game_data['team2_score']}
                                ],
                                'completed': True
                            }
                            
                            try:
                                # Settle immediately
                                settled_past_bet = settle_bet(new_past_bet, past_game_score)
                                st.session_state.bets.append(settled_past_bet)
                                save_bets(st.session_state.bets)
                                
                                result_emoji = "✅" if settled_past_bet['result'] == 'W' else ("❌" if settled_past_bet['result'] == 'L' else "➖")
                                st.success(
                                    f"{result_emoji} Bet added and settled! Result: {settled_past_bet['result']} | "
                                    f"P/L: {format_currency(settled_past_bet['profit'])}"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error settling bet: {str(e)}")
                
                st.divider()
        
        st.divider()
        
        # CSV Import Feature
        with st.expander("📥 CSV Import - Import Bets from CSV File", expanded=False):
            st.markdown("**Upload a CSV file to import multiple bets at once.**")
            st.markdown("""
            **Supported CSV Format:**
            - Columns: Team name, Bet Type, odds (spread), final (score), Michael (stake), Tim (stake)
            - Automatically groups rows into games
            - Creates bets for Michael and Tim based on stake columns
            """)
            
            uploaded_file = st.file_uploader("Choose CSV file", type=['csv'], key="csv_upload")
            
            if uploaded_file is not None:
                try:
                    df_csv = pd.read_csv(uploaded_file)
                    st.success(f"✅ CSV loaded! Found {len(df_csv)} rows.")
                    
                    # Display preview
                    st.markdown("**Preview:**")
                    st.dataframe(df_csv.head(10), width='stretch')
                    
                    if st.button("📥 Import All Bets from CSV", type="primary", use_container_width=True):
                        imported_count = 0
                        error_count = 0
                        
                        # Parse the CSV format
                        # Group rows into games (consecutive non-empty team rows)
                        games = []
                        current_game = []
                        
                        for idx, row in df_csv.iterrows():
                            team = str(row.iloc[0] if len(row) > 0 else '').strip()
                            
                            # Skip empty rows or section headers
                            if not team or team == 'NFL' or pd.isna(row.iloc[0]):
                                if current_game:
                                    games.append(current_game)
                                    current_game = []
                                continue
                            
                            # Get row data
                            bet_type = str(row.iloc[1] if len(row) > 1 else '').strip()
                            odds = row.iloc[2] if len(row) > 2 else 0
                            final_score = row.iloc[3] if len(row) > 3 else 0
                            michael_stake = row.iloc[4] if len(row) > 4 else 0
                            tim_stake = row.iloc[5] if len(row) > 5 else 0
                            
                            # Convert to proper types
                            try:
                                odds = float(odds) if not pd.isna(odds) else 0
                                final_score = float(final_score) if not pd.isna(final_score) else 0
                                michael_stake = float(michael_stake) if not pd.isna(michael_stake) and michael_stake != '' else 0
                                tim_stake = float(tim_stake) if not pd.isna(tim_stake) and tim_stake != '' else 0
                            except:
                                continue
                            
                            # Add to current game
                            current_game.append({
                                'team': team,
                                'bet_type': bet_type,
                                'spread': odds,
                                'score': final_score,
                                'michael_stake': michael_stake,
                                'tim_stake': tim_stake
                            })
                        
                        # Add last game if exists
                        if current_game:
                            games.append(current_game)
                        
                        # Process each game
                        for game_idx, game_rows in enumerate(games):
                            if len(game_rows) < 2:
                                continue
                            
                            # Get the two teams and their data
                            team1_data = game_rows[0]
                            team2_data = game_rows[1]
                            
                            team1_name = team1_data['team']
                            team2_name = team2_data['team']
                            team1_score = team1_data['score']
                            team2_score = team2_data['score']
                            
                            # Determine which is home/away (team with negative spread is usually home/favorite)
                            if team1_data['spread'] < 0:
                                home_team = team1_name
                                home_score = team1_score
                                away_team = team2_name
                                away_score = team2_score
                                home_spread = team1_data['spread']
                                away_spread = team2_data['spread']
                            else:
                                home_team = team2_name
                                home_score = team2_score
                                away_team = team1_name
                                away_score = team1_score
                                home_spread = team2_data['spread']
                                away_spread = team1_data['spread']
                            
                            game_name = f"{away_team} vs {home_team}"
                            
                            # Create bets for Michael
                            if team1_data['michael_stake'] > 0:
                                try:
                                    bet_team = team1_name
                                    bet_spread = team1_data['spread']
                                    bet_stake = team1_data['michael_stake']
                                    
                                    new_bet = {
                                        'id': len(st.session_state.bets) + imported_count + 1,
                                        'user': 'Michael',
                                        'game': game_name,
                                        'bet_type': 'Spread',
                                        'stake': bet_stake,
                                        'team': bet_team,
                                        'spread': bet_spread,
                                        'total': None,
                                        'direction': None,
                                        'result': None,
                                        'settled': False,
                                        'profit': 0,
                                        'payout': 0,
                                        'created_at': datetime.now().isoformat(),
                                        'settled_at': None,
                                        'final_score': None
                                    }
                                    
                                    game_score = {
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'scores': [
                                            {'score': home_score},
                                            {'score': away_score}
                                        ],
                                        'completed': True
                                    }
                                    
                                    settled_bet = settle_bet(new_bet, game_score)
                                    st.session_state.bets.append(settled_bet)
                                    imported_count += 1
                                except Exception as e:
                                    st.warning(f"Game {game_idx+1} - Michael bet on {team1_name}: {str(e)}")
                                    error_count += 1
                            
                            if team2_data['michael_stake'] > 0:
                                try:
                                    bet_team = team2_name
                                    bet_spread = team2_data['spread']
                                    bet_stake = team2_data['michael_stake']
                                    
                                    new_bet = {
                                        'id': len(st.session_state.bets) + imported_count + 1,
                                        'user': 'Michael',
                                        'game': game_name,
                                        'bet_type': 'Spread',
                                        'stake': bet_stake,
                                        'team': bet_team,
                                        'spread': bet_spread,
                                        'total': None,
                                        'direction': None,
                                        'result': None,
                                        'settled': False,
                                        'profit': 0,
                                        'payout': 0,
                                        'created_at': datetime.now().isoformat(),
                                        'settled_at': None,
                                        'final_score': None
                                    }
                                    
                                    game_score = {
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'scores': [
                                            {'score': home_score},
                                            {'score': away_score}
                                        ],
                                        'completed': True
                                    }
                                    
                                    settled_bet = settle_bet(new_bet, game_score)
                                    st.session_state.bets.append(settled_bet)
                                    imported_count += 1
                                except Exception as e:
                                    st.warning(f"Game {game_idx+1} - Michael bet on {team2_name}: {str(e)}")
                                    error_count += 1
                            
                            # Create bets for Tim
                            if team1_data['tim_stake'] > 0:
                                try:
                                    bet_team = team1_name
                                    bet_spread = team1_data['spread']
                                    bet_stake = team1_data['tim_stake']
                                    
                                    new_bet = {
                                        'id': len(st.session_state.bets) + imported_count + 1,
                                        'user': 'Tim',
                                        'game': game_name,
                                        'bet_type': 'Spread',
                                        'stake': bet_stake,
                                        'team': bet_team,
                                        'spread': bet_spread,
                                        'total': None,
                                        'direction': None,
                                        'result': None,
                                        'settled': False,
                                        'profit': 0,
                                        'payout': 0,
                                        'created_at': datetime.now().isoformat(),
                                        'settled_at': None,
                                        'final_score': None
                                    }
                                    
                                    game_score = {
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'scores': [
                                            {'score': home_score},
                                            {'score': away_score}
                                        ],
                                        'completed': True
                                    }
                                    
                                    settled_bet = settle_bet(new_bet, game_score)
                                    st.session_state.bets.append(settled_bet)
                                    imported_count += 1
                                except Exception as e:
                                    st.warning(f"Game {game_idx+1} - Tim bet on {team1_name}: {str(e)}")
                                    error_count += 1
                            
                            if team2_data['tim_stake'] > 0:
                                try:
                                    bet_team = team2_name
                                    bet_spread = team2_data['spread']
                                    bet_stake = team2_data['tim_stake']
                                    
                                    new_bet = {
                                        'id': len(st.session_state.bets) + imported_count + 1,
                                        'user': 'Tim',
                                        'game': game_name,
                                        'bet_type': 'Spread',
                                        'stake': bet_stake,
                                        'team': bet_team,
                                        'spread': bet_spread,
                                        'total': None,
                                        'direction': None,
                                        'result': None,
                                        'settled': False,
                                        'profit': 0,
                                        'payout': 0,
                                        'created_at': datetime.now().isoformat(),
                                        'settled_at': None,
                                        'final_score': None
                                    }
                                    
                                    game_score = {
                                        'home_team': home_team,
                                        'away_team': away_team,
                                        'scores': [
                                            {'score': home_score},
                                            {'score': away_score}
                                        ],
                                        'completed': True
                                    }
                                    
                                    settled_bet = settle_bet(new_bet, game_score)
                                    st.session_state.bets.append(settled_bet)
                                    imported_count += 1
                                except Exception as e:
                                    st.warning(f"Game {game_idx+1} - Tim bet on {team2_name}: {str(e)}")
                                    error_count += 1
                        
                        if imported_count > 0:
                            save_bets(st.session_state.bets)
                            st.balloons()
                            st.success(f"🎉 {imported_count} bet(s) imported and settled successfully!")
                            if error_count > 0:
                                st.warning(f"⚠️ {error_count} bet(s) had errors and were not imported.")
                            st.rerun()
                        else:
                            st.error("No bets were imported. Please check your CSV format.")
                            
                except Exception as e:
                    st.error(f"Error reading CSV file: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
        
        st.divider()
        
        # Bulk Entry for Past Bets
        with st.expander("📥 Bulk Entry - Enter Past Bets with Scores", expanded=True):
            st.markdown("**Enter multiple past bets at once. They will be automatically settled with the scores you provide.**")
            
            num_bets = st.number_input("Number of bets to enter", min_value=1, max_value=10, value=5, step=1, key="num_bulk_bets")
            
            # Single form for all bets
            with st.form("bulk_entry_form", clear_on_submit=True):
                bulk_bets_data = []
                
                for i in range(num_bets):
                    st.markdown(f"### Bet {i+1}")
                    col_bulk1, col_bulk2, col_bulk3 = st.columns(3)
                    
                    with col_bulk1:
                        bulk_user = st.selectbox("User", ["Michael", "Tim", "User C"], key=f"bulk_user_{i}")
                        bulk_bet_type = st.selectbox("Bet Type", ["Spread", "Over/Under"], key=f"bulk_type_{i}")
                        bulk_game = st.text_input("Game", key=f"bulk_game_{i}", placeholder="e.g., Tulane vs Ole Miss")
                        bulk_stake = st.number_input("Stake ($)", min_value=1.0, value=50.0, step=1.0, key=f"bulk_stake_{i}")
                        bulk_no_juice = st.checkbox("No Juice", value=False, key=f"bulk_no_juice_{i}")
                    
                    with col_bulk2:
                        if bulk_bet_type == "Spread":
                            bulk_team = st.text_input("Team", key=f"bulk_team_{i}", placeholder="e.g., Tulane")
                            bulk_spread = st.number_input("Spread", value=0.0, step=0.5, key=f"bulk_spread_{i}")
                            bulk_total = None
                            bulk_direction = None
                        else:
                            bulk_total = st.number_input("Total", min_value=0.0, value=50.0, step=0.5, key=f"bulk_total_{i}")
                            bulk_direction = st.selectbox("Direction", ["Over", "Under"], key=f"bulk_direction_{i}")
                            bulk_team = None
                            bulk_spread = None
                    
                    with col_bulk3:
                        st.markdown("**Final Scores:**")
                        # Parse game to get team names
                        if bulk_game:
                            if " vs " in bulk_game:
                                bulk_away, bulk_home = bulk_game.split(" vs ")
                            elif " @ " in bulk_game:
                                bulk_away, bulk_home = bulk_game.split(" @ ")
                            else:
                                parts = bulk_game.split()
                                if len(parts) >= 2:
                                    bulk_away = parts[0]
                                    bulk_home = parts[-1]
                                else:
                                    bulk_away = "Away"
                                    bulk_home = "Home"
                        else:
                            bulk_away = "Away"
                            bulk_home = "Home"
                        
                        bulk_home_score = st.number_input(
                            f"{bulk_home.strip()} Score",
                            min_value=0,
                            value=0,
                            step=1,
                            key=f"bulk_home_score_{i}"
                        )
                        bulk_away_score = st.number_input(
                            f"{bulk_away.strip()} Score",
                            min_value=0,
                            value=0,
                            step=1,
                            key=f"bulk_away_score_{i}"
                        )
                    
                    # Store bet data
                    bulk_bets_data.append({
                        'user': bulk_user,
                        'bet_type': bulk_bet_type,
                        'game': bulk_game,
                        'stake': bulk_stake,
                        'team': bulk_team if bulk_bet_type == "Spread" else None,
                        'spread': bulk_spread if bulk_bet_type == "Spread" else None,
                        'total': bulk_total if bulk_bet_type == "Over/Under" else None,
                        'direction': bulk_direction if bulk_bet_type == "Over/Under" else None,
                        'no_juice': bulk_no_juice,
                        'home_team': bulk_home.strip() if bulk_game else "Home Team",
                        'away_team': bulk_away.strip() if bulk_game else "Away Team",
                        'home_score': bulk_home_score,
                        'away_score': bulk_away_score
                    })
                    
                    if i < num_bets - 1:
                        st.divider()
                
                bulk_submitted = st.form_submit_button("💾 Add All Bets & Settle", type="primary", use_container_width=True)
                
                if bulk_submitted:
                    success_count = 0
                    error_count = 0
                    
                    for i, bet_data in enumerate(bulk_bets_data):
                        if not bet_data['game']:
                            st.warning(f"Bet {i+1}: Skipped - No game entered")
                            error_count += 1
                            continue
                        
                        if bet_data['bet_type'] == "Spread" and not bet_data['team']:
                            st.warning(f"Bet {i+1}: Skipped - No team entered for spread bet")
                            error_count += 1
                            continue
                        
                        try:
                            # Create bet
                            new_bulk_bet = {
                                'id': len(st.session_state.bets) + success_count + 1,
                                'user': bet_data['user'],
                                'game': bet_data['game'],
                                'bet_type': bet_data['bet_type'],
                                'stake': bet_data['stake'],
                                'team': bet_data['team'],
                                'spread': bet_data['spread'],
                                'total': bet_data['total'],
                                'direction': bet_data['direction'],
                                'no_juice': bet_data.get('no_juice', False),
                                'result': None,
                                'settled': False,
                                'profit': 0,
                                'payout': 0,
                                'created_at': datetime.now().isoformat(),
                                'settled_at': None,
                                'final_score': None
                            }
                            
                            # Create game_score for immediate settlement
                            bulk_game_score = {
                                'home_team': bet_data['home_team'],
                                'away_team': bet_data['away_team'],
                                'scores': [
                                    {'score': bet_data['home_score']},
                                    {'score': bet_data['away_score']}
                                ],
                                'completed': True
                            }
                            
                            # Settle immediately
                            settled_bulk_bet = settle_bet(new_bulk_bet, bulk_game_score)
                            st.session_state.bets.append(settled_bulk_bet)
                            success_count += 1
                            
                            result_emoji = "✅" if settled_bulk_bet['result'] == 'W' else ("❌" if settled_bulk_bet['result'] == 'L' else "➖")
                            st.success(
                                f"{result_emoji} Bet {i+1} ({bet_data['game']}): {settled_bulk_bet['result']} | "
                                f"P/L: {format_currency(settled_bulk_bet['profit'])}"
                            )
                        except Exception as e:
                            st.error(f"Bet {i+1} ({bet_data.get('game', 'Unknown')}): Error - {str(e)}")
                            error_count += 1
                    
                    if success_count > 0:
                        save_bets(st.session_state.bets)
                        st.balloons()
                        st.success(f"🎉 {success_count} bet(s) added and settled successfully!")
                        if error_count > 0:
                            st.warning(f"⚠️ {error_count} bet(s) had errors and were not added.")
                        st.rerun()
                    else:
                        st.error("No bets were added. Please check your inputs.")
        
        st.divider()
        
        # Bet form
        with st.form("bet_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                user = st.selectbox("User", ["Michael", "Tim", "User C"], key="bet_user")
                bet_type = st.selectbox("Bet Type", ["Spread", "Over/Under"], key="bet_type")
                game = st.text_input("Game (e.g., 'Oklahoma vs Alabama')", key="bet_game")
            
            with col2:
                stake = st.number_input("Stake ($)", min_value=1.0, value=50.0, step=1.0, key="bet_stake")
                no_juice = st.checkbox("No Juice (Loss = Stake only, no 10% penalty)", value=False, key="bet_no_juice")
                
                if bet_type == "Spread":
                    team = st.text_input("Team", key="bet_team")
                    spread = st.number_input("Spread", value=0.0, step=0.5, key="bet_spread")
                    total = None
                    direction = None
                else:  # Over/Under
                    total = st.number_input("Total", min_value=0.0, value=50.0, step=0.5, key="bet_total")
                    direction = st.selectbox("Direction", ["Over", "Under"], key="bet_direction")
                    team = None
                    spread = None
            
            submitted = st.form_submit_button("Place Bet", use_container_width=True)
            
            if submitted:
                if not game:
                    st.error("Please enter a game")
                elif bet_type == "Spread" and not team:
                    st.error("Please enter a team for spread bets")
                else:
                    new_bet = {
                        'id': len(st.session_state.bets) + 1,
                        'user': user,
                        'game': game,
                        'bet_type': bet_type,
                        'stake': stake,
                        'team': team,
                        'spread': spread,
                        'total': total,
                        'direction': direction,
                        'no_juice': no_juice,
                        'result': None,
                        'settled': False,
                        'profit': 0,
                        'payout': 0,
                        'created_at': datetime.now().isoformat(),
                        'settled_at': None,
                        'final_score': None
                    }
                    
                    st.session_state.bets.append(new_bet)
                    save_bets(st.session_state.bets)
                    st.success(f"✅ Bet placed! {user} bet ${stake} on {game}")
                    st.rerun()
    
    # ============================================================================
    # TAB 3: ALL BETS
    # ============================================================================
    with tab3:
        st.header("📋 All Bets")
        
        # Manual Settlement Section
        with st.expander("⚖️ Manual Settlement", expanded=True):
            st.markdown("**Manually settle a bet by entering final scores**")
            
            # Get pending bets for selection
            pending_bets = [b for b in st.session_state.bets if not b.get('settled', False)]
            
            # Always show the form - use dropdown if bets exist, otherwise allow manual entry
            if pending_bets:
                # Create bet selection dropdown
                bet_options = {}
                for bet in pending_bets:
                    user_display = st.session_state.user_names.get(bet.get('user', ''), bet.get('user', ''))
                    if bet['bet_type'] == "Spread":
                        bet_desc = f"{bet.get('game', '')} - {user_display}: {bet.get('team', '')} {bet.get('spread', 0):+.1f}"
                    else:
                        bet_desc = f"{bet.get('game', '')} - {user_display}: {bet.get('direction', '')} {bet.get('total', 0)}"
                    bet_options[bet['id']] = bet_desc
                
                selected_bet_id = st.selectbox(
                    "Select Bet to Settle",
                    options=list(bet_options.keys()),
                    format_func=lambda x: bet_options[x],
                    key="manual_settle_bet"
                )
                
                if selected_bet_id:
                    selected_bet = next(b for b in pending_bets if b['id'] == selected_bet_id)
                    
                    # Parse game to get team names
                    game_str = selected_bet.get('game', '')
                    if " vs " in game_str:
                        away_team, home_team = game_str.split(" vs ")
                    elif " @ " in game_str:
                        away_team, home_team = game_str.split(" @ ")
                    else:
                        # Try to parse other formats
                        parts = game_str.split()
                        if len(parts) >= 2:
                            away_team = parts[0]
                            home_team = parts[-1]
                        else:
                            away_team = "Away Team"
                            home_team = "Home Team"
                    
                    # Score input form
                    with st.form("manual_settle_form"):
                        st.markdown(f"**Game:** {selected_bet.get('game', '')}")
                        st.markdown(f"**Bet:** {bet_options[selected_bet_id]}")
                        st.markdown(f"**Stake:** ${selected_bet.get('stake', 0):,.2f}")
                        
                        # Determine which team is which (doesn't matter the order)
                        team1 = home_team.strip()
                        team2 = away_team.strip()
                        
                        col_score1, col_score2 = st.columns(2)
                        with col_score1:
                            team1_score_input = st.number_input(
                                f"{team1} Score",
                                min_value=0,
                                value=0,
                                step=1,
                                key="manual_team1_score"
                            )
                        with col_score2:
                            team2_score_input = st.number_input(
                                f"{team2} Score",
                                min_value=0,
                                value=0,
                                step=1,
                                key="manual_team2_score"
                            )
                        
                        submitted_settle = st.form_submit_button("Settle Bet", type="primary", use_container_width=True)
                        
                        if submitted_settle:
                            # Create game_score dict for settlement
                            # Order doesn't matter - just need two teams and two scores
                            manual_game_score = {
                                'home_team': team1,
                                'away_team': team2,
                                'scores': [
                                    {'score': team1_score_input},
                                    {'score': team2_score_input}
                                ],
                                'completed': True
                            }
                            
                            try:
                                # Settle the bet
                                settled_bet = settle_bet(selected_bet, manual_game_score)
                                
                                # Update the bet in session state
                                for i, bet in enumerate(st.session_state.bets):
                                    if bet['id'] == selected_bet_id:
                                        st.session_state.bets[i] = settled_bet
                                        break
                                
                                # Save to file
                                save_bets(st.session_state.bets)
                                
                                result_emoji = "✅" if settled_bet['result'] == 'W' else ("❌" if settled_bet['result'] == 'L' else "➖")
                                st.success(
                                    f"{result_emoji} Bet settled! Result: {settled_bet['result']} | "
                                    f"P/L: {format_currency(settled_bet['profit'])} | "
                                    f"Final Score: {settled_bet['final_score']}"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error settling bet: {str(e)}")
            else:
                st.info("ℹ️ No pending bets found. All bets are already settled or you haven't placed any bets yet.")
                st.markdown("**To settle a bet, first place a bet in the 'Place Bet' tab, then come back here to settle it.**")
            
            # Option to re-settle already settled bets (for corrections)
            st.markdown("---")
            st.caption("💡 Need to correct a settled bet? You can re-settle it below.")
            
            settled_bets_list = [b for b in st.session_state.bets if b.get('settled', False)]
            
            if settled_bets_list:
                settled_bet_options = {}
                for bet in settled_bets_list:
                    user_display = st.session_state.user_names.get(bet.get('user', ''), bet.get('user', ''))
                    if bet['bet_type'] == "Spread":
                        bet_desc = f"{bet.get('game', '')} - {user_display}: {bet.get('team', '')} {bet.get('spread', 0):+.1f} [{bet.get('result', '-')}]"
                    else:
                        bet_desc = f"{bet.get('game', '')} - {user_display}: {bet.get('direction', '')} {bet.get('total', 0)} [{bet.get('result', '-')}]"
                    settled_bet_options[bet['id']] = bet_desc
                
                selected_settled_id = st.selectbox(
                    "Select Settled Bet to Re-Settle",
                    options=list(settled_bet_options.keys()),
                    format_func=lambda x: settled_bet_options[x],
                    key="manual_resettle_bet"
                )
                
                if selected_settled_id:
                    selected_settled_bet = next(b for b in settled_bets_list if b['id'] == selected_settled_id)
                    
                    # Parse game to get team names
                    game_str_settled = selected_settled_bet.get('game', '')
                    if " vs " in game_str_settled:
                        away_team_settled, home_team_settled = game_str_settled.split(" vs ")
                    elif " @ " in game_str_settled:
                        away_team_settled, home_team_settled = game_str_settled.split(" @ ")
                    else:
                        parts = game_str_settled.split()
                        if len(parts) >= 2:
                            away_team_settled = parts[0]
                            home_team_settled = parts[-1]
                        else:
                            away_team_settled = "Away Team"
                            home_team_settled = "Home Team"
                    
                    # Get current score if available
                    current_score = selected_settled_bet.get('final_score', '')
                    default_home = 0
                    default_away = 0
                    if current_score and '-' in current_score:
                        try:
                            # Try to parse existing score
                            score_parts = current_score.split('-')
                            if len(score_parts) >= 2:
                                default_home = int(score_parts[0].split()[-1])
                                default_away = int(score_parts[1].split()[0])
                        except:
                            pass
                    
                    # Score input form for re-settlement
                    with st.form("manual_resettle_form"):
                        st.markdown(f"**Game:** {selected_settled_bet.get('game', '')}")
                        st.markdown(f"**Current Result:** {selected_settled_bet.get('result', '-')} | P/L: {format_currency(selected_settled_bet.get('profit', 0))}")
                        st.markdown(f"**Current Score:** {current_score if current_score else 'N/A'}")
                        
                        # Determine team names (order doesn't matter)
                        reset_team1 = home_team_settled.strip()
                        reset_team2 = away_team_settled.strip()
                        
                        col_score1_reset, col_score2_reset = st.columns(2)
                        with col_score1_reset:
                            team1_score_reset = st.number_input(
                                f"{reset_team1} Score",
                                min_value=0,
                                value=default_home,
                                step=1,
                                key="manual_team1_score_reset"
                            )
                        with col_score2_reset:
                            team2_score_reset = st.number_input(
                                f"{reset_team2} Score",
                                min_value=0,
                                value=default_away,
                                step=1,
                                key="manual_team2_score_reset"
                            )
                        
                        submitted_resettle = st.form_submit_button("Re-Settle Bet", type="primary", use_container_width=True)
                        
                        if submitted_resettle:
                            # Create game_score dict for re-settlement
                            manual_game_score_reset = {
                                'home_team': reset_team1,
                                'away_team': reset_team2,
                                'scores': [
                                    {'score': team1_score_reset},
                                    {'score': team2_score_reset}
                                ],
                                'completed': True
                            }
                            
                            try:
                                # Re-settle the bet (reset settled status first)
                                bet_to_resettle = selected_settled_bet.copy()
                                bet_to_resettle['settled'] = False
                                
                                settled_bet_reset = settle_bet(bet_to_resettle, manual_game_score_reset)
                                
                                # Update the bet in session state
                                for i, bet in enumerate(st.session_state.bets):
                                    if bet['id'] == selected_settled_id:
                                        st.session_state.bets[i] = settled_bet_reset
                                        break
                                
                                # Save to file
                                save_bets(st.session_state.bets)
                                
                                result_emoji_reset = "✅" if settled_bet_reset['result'] == 'W' else ("❌" if settled_bet_reset['result'] == 'L' else "➖")
                                st.success(
                                    f"{result_emoji_reset} Bet re-settled! New Result: {settled_bet_reset['result']} | "
                                    f"New P/L: {format_currency(settled_bet_reset['profit'])} | "
                                    f"Final Score: {settled_bet_reset['final_score']}"
                                )
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error re-settling bet: {str(e)}")
            else:
                st.caption("No settled bets available for re-settlement.")
        
        st.divider()
        
        # Delete Bet Section
        with st.expander("🗑️ Delete Bet (Remove Bad/Error Bets)", expanded=False):
            st.markdown("**Select a bet to delete. This cannot be undone!**")
            
            if st.session_state.bets:
                # Create bet selection dropdown
                delete_bet_options = {}
                for bet in st.session_state.bets:
                    user_display = st.session_state.user_names.get(bet.get('user', ''), bet.get('user', ''))
                    if bet['bet_type'] == "Spread":
                        bet_desc = f"ID {bet.get('id', '?')}: {bet.get('game', '')} - {user_display}: {bet.get('team', '')} {bet.get('spread', 0):+.1f} | ${bet.get('stake', 0):,.2f}"
                    else:
                        bet_desc = f"ID {bet.get('id', '?')}: {bet.get('game', '')} - {user_display}: {bet.get('direction', '')} {bet.get('total', 0)} | ${bet.get('stake', 0):,.2f}"
                    delete_bet_options[bet['id']] = bet_desc
                
                selected_delete_id = st.selectbox(
                    "Select Bet to Delete",
                    options=list(delete_bet_options.keys()),
                    format_func=lambda x: delete_bet_options[x],
                    key="delete_bet_select"
                )
                
                if selected_delete_id:
                    bet_to_delete = next(b for b in st.session_state.bets if b['id'] == selected_delete_id)
                    user_display_del = st.session_state.user_names.get(bet_to_delete.get('user', ''), bet_to_delete.get('user', ''))
                    
                    st.warning(f"⚠️ **You are about to delete:**")
                    st.write(f"- **User:** {user_display_del}")
                    st.write(f"- **Game:** {bet_to_delete.get('game', '')}")
                    if bet_to_delete['bet_type'] == "Spread":
                        st.write(f"- **Bet:** {bet_to_delete.get('team', '')} {bet_to_delete.get('spread', 0):+.1f}")
                    else:
                        st.write(f"- **Bet:** {bet_to_delete.get('direction', '')} {bet_to_delete.get('total', 0)}")
                    st.write(f"- **Stake:** ${bet_to_delete.get('stake', 0):,.2f}")
                    st.write(f"- **Status:** {'Settled' if bet_to_delete.get('settled', False) else 'Pending'}")
                    if bet_to_delete.get('settled', False):
                        st.write(f"- **Result:** {bet_to_delete.get('result', '-')} | **P/L:** {format_currency(bet_to_delete.get('profit', 0))}")
                    
                    col_del1, col_del2 = st.columns(2)
                    with col_del1:
                        if st.button("🗑️ Delete This Bet", type="primary", use_container_width=True, key="confirm_delete"):
                            # Remove bet from session state
                            st.session_state.bets = [b for b in st.session_state.bets if b['id'] != selected_delete_id]
                            save_bets(st.session_state.bets)
                            st.success(f"✅ Bet deleted successfully!")
                            st.rerun()
                    with col_del2:
                        if st.button("Cancel", use_container_width=True, key="cancel_delete"):
                            st.info("Deletion cancelled.")
            else:
                st.info("No bets to delete.")
        
        st.divider()
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_user = st.selectbox("Filter by User", ["All", "Michael", "Tim", "User C"], key="filter_user")
        with col2:
            filter_status = st.selectbox("Filter by Status", ["All", "Pending", "Settled"], key="filter_status")
        with col3:
            filter_result = st.selectbox("Filter by Result", ["All", "W", "L", "P"], key="filter_result")
        
        # Filter bets
        filtered_bets = st.session_state.bets.copy()
        if filter_user != "All":
            filtered_bets = [b for b in filtered_bets if b.get('user') == filter_user]
        if filter_status == "Pending":
            filtered_bets = [b for b in filtered_bets if not b.get('settled', False)]
        elif filter_status == "Settled":
            filtered_bets = [b for b in filtered_bets if b.get('settled', False)]
        if filter_result != "All":
            filtered_bets = [b for b in filtered_bets if b.get('result') == filter_result]
        
        # Display bets
        if filtered_bets:
            bets_data = []
            for bet in reversed(filtered_bets):  # Most recent first
                user_display = st.session_state.user_names.get(bet.get('user', ''), bet.get('user', ''))
                
                if bet['bet_type'] == "Spread":
                    bet_desc = f"{bet.get('team', '')} {bet.get('spread', 0):+.1f}"
                else:
                    bet_desc = f"{bet.get('direction', '')} {bet.get('total', 0)}"
                
                status = "✅ Settled" if bet.get('settled', False) else "⏳ Pending"
                result = bet.get('result', '-')
                
                bets_data.append({
                    'ID': bet.get('id', '?'),
                    'User': user_display,
                    'Game': bet.get('game', ''),
                    'Bet': bet_desc,
                    'Stake': f"${bet.get('stake', 0):,.2f}",
                    'Status': status,
                    'Result': result,
                    'Profit': format_currency(bet.get('profit', 0)),
                    'Final Score': bet.get('final_score', '-')
                })
            
            df = pd.DataFrame(bets_data)
            st.dataframe(df, width='stretch', hide_index=True)
            
            # Export button for filtered bets
            st.divider()
            csv_filtered = df.to_csv(index=False)
            filter_label = f"_{filter_user}" if filter_user != "All" else ""
            filter_status_label = f"_{filter_status}" if filter_status != "All" else ""
            filter_result_label = f"_{filter_result}" if filter_result != "All" else ""
            filename = f"bets{filter_label}{filter_status_label}{filter_result_label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            st.download_button(
                label="📥 Export Filtered Bets to CSV",
                data=csv_filtered,
                file_name=filename,
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.info("No bets found matching filters.")
    
    # ============================================================================
    # TAB 4: GAMES & ODDS
    # ============================================================================
    with tab4:
        st.header("🎮 FanDuel Games & Odds")
        st.markdown("**View FanDuel lines and create bets with one click**")
        
        # Refresh button
        if st.button("🔄 Refresh FanDuel Odds", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        odds_data = fetch_odds(API_KEY, sport_key)
        
        if odds_data:
            for event in odds_data:
                home = event.get('home_team', '')
                away = event.get('away_team', '')
                commence_time = event.get('commence_time', '')
                game_id = f"{away} vs {home}"
                
                # Find FanDuel odds
                fanduel_odds = None
                for bm in event.get('bookmakers', []):
                    if bm.get('title', '').lower() == 'fanduel':
                        fanduel_odds = bm
                        break
                
                if not fanduel_odds:
                    # Use first bookmaker if FanDuel not found
                    fanduel_odds = event.get('bookmakers', [{}])[0] if event.get('bookmakers') else {}
                
                markets = {m['key']: m for m in fanduel_odds.get('markets', [])}
                
                # Extract spreads
                home_spread = None
                away_spread = None
                home_spread_odds = None
                away_spread_odds = None
                if 'spreads' in markets:
                    spreads = markets['spreads'].get('outcomes', [])
                    for spread in spreads:
                        if spread.get('name') == home:
                            home_spread = spread.get('point', 0)
                            home_spread_odds = spread.get('price', 0)
                        elif spread.get('name') == away:
                            away_spread = spread.get('point', 0)
                            away_spread_odds = spread.get('price', 0)
                
                # Extract totals
                total_line = None
                over_odds = None
                under_odds = None
                if 'totals' in markets:
                    totals = markets['totals'].get('outcomes', [])
                    for total in totals:
                        if total.get('name') == 'Over':
                            total_line = total.get('point', 0)
                            over_odds = total.get('price', 0)
                        elif total.get('name') == 'Under':
                            under_odds = total.get('price', 0)
                
                # Display game card with quick bet form
                with st.container():
                    st.markdown(f"### {game_id}")
                    if commence_time:
                        st.caption(f"⏰ {commence_time[:16]}")
                    
                    col_game1, col_game2, col_game3 = st.columns(3)
                    
                    with col_game1:
                        st.markdown(f"**{away}**")
                        if away_spread is not None:
                            st.write(f"Spread: {away_spread:+.1f} ({away_spread_odds:+d})")
                        st.markdown("---")
                        st.markdown(f"**{home}**")
                        if home_spread is not None:
                            st.write(f"Spread: {home_spread:+.1f} ({home_spread_odds:+d})")
                    
                    with col_game2:
                        st.markdown("**Totals**")
                        if total_line is not None:
                            st.write(f"Over {total_line:.1f} ({over_odds:+d})")
                            st.write(f"Under {total_line:.1f} ({under_odds:+d})")
                    
                    with col_game3:
                        st.markdown("**Quick Bet**")
                        
                        # Quick bet form
                        with st.form(f"quick_bet_{game_id.replace(' ', '_')}", clear_on_submit=True):
                            quick_user = st.selectbox("User", ["Michael", "Tim", "User C"], key=f"quick_user_{game_id}")
                            quick_bet_type = st.selectbox("Bet Type", ["Spread", "Over/Under"], key=f"quick_type_{game_id}")
                            
                            if quick_bet_type == "Spread":
                                quick_team = st.selectbox("Team", [away, home], key=f"quick_team_{game_id}")
                                if quick_team == home and home_spread is not None:
                                    quick_spread = st.number_input("Spread", value=float(home_spread), step=0.5, key=f"quick_spread_{game_id}")
                                elif quick_team == away and away_spread is not None:
                                    quick_spread = st.number_input("Spread", value=float(away_spread), step=0.5, key=f"quick_spread_{game_id}")
                                else:
                                    quick_spread = st.number_input("Spread", value=0.0, step=0.5, key=f"quick_spread_{game_id}")
                                quick_total = None
                                quick_direction = None
                            else:
                                if total_line is not None:
                                    quick_total = st.number_input("Total", value=float(total_line), step=0.5, key=f"quick_total_{game_id}")
                                else:
                                    quick_total = st.number_input("Total", value=50.0, step=0.5, key=f"quick_total_{game_id}")
                                quick_direction = st.selectbox("Direction", ["Over", "Under"], key=f"quick_dir_{game_id}")
                                quick_team = None
                                quick_spread = None
                            
                            quick_stake = st.number_input("Stake ($)", min_value=1.0, value=50.0, step=1.0, key=f"quick_stake_{game_id}")
                            quick_no_juice = st.checkbox("No Juice", value=False, key=f"quick_no_juice_{game_id}")
                            
                            quick_submitted = st.form_submit_button("Place Bet", type="primary", use_container_width=True)
                            
                            if quick_submitted:
                                new_quick_bet = {
                                    'id': len(st.session_state.bets) + 1,
                                    'user': quick_user,
                                    'game': game_id,
                                    'bet_type': quick_bet_type,
                                    'stake': quick_stake,
                                    'team': quick_team,
                                    'spread': quick_spread,
                                    'total': quick_total,
                                    'direction': quick_direction,
                                    'no_juice': quick_no_juice,
                                    'result': None,
                                    'settled': False,
                                    'profit': 0,
                                    'payout': 0,
                                    'created_at': datetime.now().isoformat(),
                                    'settled_at': None,
                                    'final_score': None
                                }
                                
                                st.session_state.bets.append(new_quick_bet)
                                save_bets(st.session_state.bets)
                                st.success(f"✅ Bet placed! {quick_user} bet ${quick_stake} on {game_id}")
                                st.rerun()
                    
                    st.divider()
            
            if not odds_data:
                st.info("No games found.")
        else:
            st.warning("Could not fetch odds data. Check API key and connection.")
            st.info("💡 **Tip:** The Odds API provides FanDuel lines. Make sure your API key is valid.")
    
    # ============================================================================
    # TAB 5: DANNY
    # ============================================================================
    with tab5:
        st.header("💰 Danny - Bets with Juice")
        st.markdown("**All bets that have juice applied (No Juice NOT checked). Running tally of money owed.**")
        
        # Filter bets: Only bets where no_juice is False or not set (defaults to False)
        danny_bets = [
            b for b in st.session_state.bets 
            if not b.get('no_juice', False)  # Only bets WITH juice
        ]
        
        # Sort by date (oldest first for running tally)
        danny_bets_sorted = sorted(danny_bets, key=lambda x: x.get('created_at', ''))
        
        if danny_bets_sorted:
            st.markdown(f"**Total Bets with Juice: {len(danny_bets_sorted)}**")
            
            # Calculate running totals
            running_total = 0.0
            running_tally_data = []
            
            for bet in danny_bets_sorted:
                user_display = st.session_state.user_names.get(bet.get('user', ''), bet.get('user', ''))
                
                # Get bet description
                if bet['bet_type'] == "Spread":
                    bet_desc = f"{bet.get('team', '')} {bet.get('spread', 0):+.1f}"
                else:
                    bet_desc = f"{bet.get('direction', '')} {bet.get('total', 0)}"
                
                # Get date
                created_date = bet.get('created_at', '')
                if created_date:
                    try:
                        date_obj = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                        date_str = date_obj.strftime('%Y-%m-%d')
                    except:
                        date_str = created_date[:10] if len(created_date) >= 10 else 'N/A'
                else:
                    date_str = 'N/A'
                
                # Get profit (0 if not settled)
                profit = bet.get('profit', 0) if bet.get('settled', False) else 0
                running_total += profit
                
                # Status
                if bet.get('settled', False):
                    status = f"{bet.get('result', '-')} | {format_currency(profit)}"
                    status_color = "green" if profit >= 0 else "red"
                else:
                    status = "⏳ Pending"
                    status_color = "gray"
                
                running_tally_data.append({
                    'Date': date_str,
                    'User': user_display,
                    'Game': bet.get('game', ''),
                    'Bet': bet_desc,
                    'Stake': f"${bet.get('stake', 0):,.2f}",
                    'Status': status,
                    'Profit': format_currency(profit),
                    'Running Total': format_currency(running_total)
                })
            
            # Display as dataframe
            df_danny = pd.DataFrame(running_tally_data)
            st.dataframe(df_danny, width='stretch', hide_index=True)
            
            # Export button for Danny
            st.divider()
            csv_danny = df_danny.to_csv(index=False)
            st.download_button(
                label="📥 Export Danny Bets to CSV",
                data=csv_danny,
                file_name=f"danny_bets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            # Summary section
            st.divider()
            st.markdown("### 📊 Summary")
            
            col_sum1, col_sum2, col_sum3 = st.columns(3)
            
            with col_sum1:
                settled_danny = [b for b in danny_bets_sorted if b.get('settled', False)]
                total_settled = len(settled_danny)
                st.metric("Settled Bets", total_settled)
            
            with col_sum2:
                pending_danny = [b for b in danny_bets_sorted if not b.get('settled', False)]
                total_pending = len(pending_danny)
                st.metric("Pending Bets", total_pending)
            
            with col_sum3:
                # Final running total (only from settled bets)
                final_total = sum([b.get('profit', 0) for b in settled_danny])
                total_color = "green" if final_total >= 0 else "red"
                st.markdown(
                    f"<h2 style='color: {total_color};'>Final Total: {format_currency(final_total)}</h2>",
                    unsafe_allow_html=True
                )
            
            # Detailed breakdown
            st.markdown("---")
            st.markdown("### 💵 Detailed Breakdown")
            
            col_break1, col_break2 = st.columns(2)
            
            with col_break1:
                st.markdown("**By User:**")
                user_totals = {}
                for bet in settled_danny:
                    user = bet.get('user', '')
                    user_display = st.session_state.user_names.get(user, user)
                    profit = bet.get('profit', 0)
                    if user_display not in user_totals:
                        user_totals[user_display] = 0
                    user_totals[user_display] += profit
                
                for user, total in sorted(user_totals.items(), key=lambda x: x[1], reverse=True):
                    color = "green" if total >= 0 else "red"
                    st.markdown(f"- **{user}**: <span style='color: {color};'>{format_currency(total)}</span>", unsafe_allow_html=True)
            
            with col_break2:
                st.markdown("**By Result:**")
                wins = len([b for b in settled_danny if b.get('result') == 'W'])
                losses = len([b for b in settled_danny if b.get('result') == 'L'])
                pushes = len([b for b in settled_danny if b.get('result') == 'P'])
                
                st.write(f"- **Wins:** {wins}")
                st.write(f"- **Losses:** {losses}")
                st.write(f"- **Pushes:** {pushes}")
                
                if wins + losses > 0:
                    win_rate = (wins / (wins + losses)) * 100
                    st.write(f"- **Win Rate:** {win_rate:.1f}%")
        else:
            st.info("No bets with juice found. All bets have 'No Juice' checked.")
            st.caption("💡 **Tip:** Bets with juice are those where the 'No Juice' checkbox is NOT checked.")

if __name__ == "__main__":
    main()
