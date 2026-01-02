"""
Script to import bets from filtered CSV export to Supabase
This handles the CSV format from the "All Bets" export
"""
import csv
import re
from io import StringIO
from supabase import create_client, Client
from datetime import datetime

# Supabase configuration
SUPABASE_URL = "https://xtgfwmjdcomlmqbqdabl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0Z2Z3bWpkY29tbG1xYnFkYWJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY0NDA2NDAsImV4cCI6MjA4MjAxNjY0MH0.Ub_nq8BqJUb6cLqb9nor7T6-jD75_VLmiJBjtTHGFjk"

def parse_bet_string(bet_str):
    """Parse bet string like 'Miami +7.5' or 'OSU -7.5' into team and spread"""
    # Remove extra whitespace
    bet_str = bet_str.strip()
    
    # Pattern: Team name followed by + or - and a number
    # Examples: "Miami +7.5", "OSU -7.5", "Ole Miss Rebels +6.0"
    match = re.match(r'(.+?)\s*([+-])(\d+\.?\d*)', bet_str)
    if match:
        team = match.group(1).strip()
        sign = match.group(2)
        spread_value = float(match.group(3))
        
        # If negative sign, make spread negative
        if sign == '-':
            spread = -spread_value
        else:
            spread = spread_value
        
        return team, spread
    
    return None, None

def parse_profit(profit_str):
    """Parse profit string like '+$50.00' or '$-55.00' into float"""
    if not profit_str or profit_str == '':
        return 0.0
    
    # Remove $ and + signs, keep - sign
    profit_str = profit_str.replace('$', '').replace('+', '').strip()
    try:
        return float(profit_str)
    except:
        return 0.0

def parse_stake(stake_str):
    """Parse stake string like '$50.00' into float"""
    if not stake_str:
        return 50.0
    
    stake_str = stake_str.replace('$', '').strip()
    try:
        return float(stake_str)
    except:
        return 50.0

def import_filtered_csv(csv_file_path):
    """Import bets from filtered CSV export to Supabase"""
    # Connect to Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    bets_to_insert = []
    seen_ids = set()  # Track IDs to avoid duplicates
    
    # Read the CSV file
    print(f"Reading CSV file: {csv_file_path}")
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row_num, row in enumerate(reader, start=2):
            try:
                # Skip if ID already seen (duplicate)
                bet_id = row.get('ID', '').strip()
                if bet_id and bet_id in seen_ids:
                    print(f"Skipping row {row_num}: Duplicate ID {bet_id}")
                    continue
                if bet_id:
                    seen_ids.add(bet_id)
                
                # Extract basic info
                user = row.get('User', '').strip()
                game = row.get('Game', '').strip()
                bet_str = row.get('Bet', '').strip()
                stake_str = row.get('Stake', '$50.00')
                status_str = row.get('Status', '').strip()
                result_str = row.get('Result', '').strip()
                profit_str = row.get('Profit', '+$0.00')
                final_score = row.get('Final Score', '').strip()
                
                if not user or not game or not bet_str:
                    print(f"Skipping row {row_num}: Missing required fields")
                    continue
                
                # Parse bet details
                team, spread = parse_bet_string(bet_str)
                if not team or spread is None:
                    print(f"Skipping row {row_num}: Could not parse bet '{bet_str}'")
                    continue
                
                # Determine if settled
                settled = '✅ Settled' in status_str or 'Settled' in status_str
                
                # Parse result
                result = result_str.strip() if result_str else ''
                if not result and settled:
                    # Try to infer from profit
                    profit = parse_profit(profit_str)
                    if profit > 0:
                        result = 'W'
                    elif profit < 0:
                        result = 'L'
                    else:
                        result = 'P'
                
                # Parse profit and stake
                profit = parse_profit(profit_str)
                stake = parse_stake(stake_str)
                
                # Calculate payout
                payout = profit if result == 'W' else 0.0
                
                # Determine no_juice - if profit matches stake exactly (no juice applied on loss)
                # For losses with juice: profit = -stake * 1.1
                # For losses without juice: profit = -stake
                no_juice = False
                if result == 'L' and profit == -stake:
                    no_juice = True
                elif result == 'L' and profit == -(stake * 1.1):
                    no_juice = False
                # Default: assume juice is applied unless we can determine otherwise
                
                # Create bet object
                bet = {
                    'user': user,
                    'game': game,
                    'bet_type': 'Spread',  # All bets in this CSV are spreads
                    'stake': stake,
                    'team': team,
                    'spread': spread,
                    'total': None,
                    'direction': None,
                    'no_juice': no_juice,
                    'result': result,
                    'settled': settled,
                    'profit': profit,
                    'payout': payout,
                    'created_at': datetime.now().isoformat(),
                    'settled_at': datetime.now().isoformat() if settled else None,
                    'final_score': final_score if final_score else ''
                }
                
                bets_to_insert.append(bet)
                print(f"✓ Row {row_num}: {user} - {game} - {team} {spread:+g} - {result} - ${profit:.2f}")
                
            except Exception as e:
                print(f"✗ Error parsing row {row_num}: {e}")
                print(f"  Row data: {row}")
                continue
    
    print(f"\nPrepared {len(bets_to_insert)} bets for insertion")
    
    if not bets_to_insert:
        print("No bets to insert!")
        return
    
    # Clear existing bets
    print("\nClearing existing bets from Supabase...")
    try:
        supabase.table("bets").delete().neq("id", -1).execute()
        print("✓ Existing bets cleared")
    except Exception as e:
        print(f"Warning: Could not clear existing bets: {e}")
    
    # Insert all bets
    print(f"\nInserting {len(bets_to_insert)} bets into Supabase...")
    try:
        response = supabase.table("bets").insert(bets_to_insert).execute()
        print(f"✓ Successfully inserted {len(bets_to_insert)} bets!")
        print(f"Response: {len(response.data)} bets in database")
    except Exception as e:
        print(f"✗ Error inserting bets: {e}")
        raise

if __name__ == "__main__":
    print("=" * 50)
    print("FILTERED CSV BET IMPORT SCRIPT")
    print("=" * 50)
    csv_path = r"c:\Users\JMJsm\Downloads\bets_20260102_010417.csv"
    import_filtered_csv(csv_path)
    print("=" * 50)
    print("Import complete!")
    print("=" * 50)

