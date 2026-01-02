"""
Script to restore bets from JSON file to Supabase
"""
import json
from supabase import create_client, Client

# Supabase configuration - you'll need to set these
SUPABASE_URL = "https://xtgfwmjdcomlmqbqdabl.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh0Z2Z3bWpkY29tbG1xYnFkYWJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY0NDA2NDAsImV4cCI6MjA4MjAxNjY0MH0.Ub_nq8BqJUb6cLqb9nor7T6-jD75_VLmiJBjtTHGFjk"

def restore_bets():
    """Restore bets from JSON file to Supabase"""
    # Read the JSON file
    with open('bets_data.json', 'r') as f:
        bets = json.load(f)
    
    print(f"Found {len(bets)} bets in JSON file")
    
    # Connect to Supabase
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Convert user names: User A -> Michael, User B -> Tim
    user_mapping = {
        "User A": "Michael",
        "User B": "Tim"
    }
    
    # Prepare bets for insertion
    bets_to_insert = []
    for bet in bets:
        # Create a copy without the 'id' field (Supabase will auto-generate)
        new_bet = {k: v for k, v in bet.items() if k != 'id'}
        
        # Update user name if needed
        if new_bet.get('user') in user_mapping:
            new_bet['user'] = user_mapping[new_bet['user']]
        
        bets_to_insert.append(new_bet)
    
    print(f"Prepared {len(bets_to_insert)} bets for insertion")
    print(f"User mapping: {user_mapping}")
    
    # Clear existing bets
    print("Clearing existing bets from Supabase...")
    try:
        supabase.table("bets").delete().neq("id", -1).execute()
        print("✓ Existing bets cleared")
    except Exception as e:
        print(f"Warning: Could not clear existing bets: {e}")
    
    # Insert all bets
    print("Inserting bets into Supabase...")
    try:
        if bets_to_insert:
            response = supabase.table("bets").insert(bets_to_insert).execute()
            print(f"✓ Successfully inserted {len(bets_to_insert)} bets!")
            print(f"Response: {len(response.data)} bets in database")
        else:
            print("No bets to insert")
    except Exception as e:
        print(f"✗ Error inserting bets: {e}")
        raise

if __name__ == "__main__":
    print("=" * 50)
    print("BET RESTORATION SCRIPT")
    print("=" * 50)
    restore_bets()
    print("=" * 50)
    print("Restoration complete!")
    print("=" * 50)

