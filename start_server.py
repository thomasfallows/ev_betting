import requests
from config import API_KEY, SPORTS_CONFIG

def test_api():
    """Test if the Odds API is working"""
    print("Testing Odds API...")
    print(f"API Key: {'Set' if API_KEY else 'NOT SET!'}")
    
    if not API_KEY:
        print("\nERROR: No API key found!")
        print("Please add ODDS_API_KEY to your .env file")
        return
    
    # Test MLB endpoint
    print("\nTesting MLB endpoint...")
    mlb_config = SPORTS_CONFIG['mlb']
    url = f"{mlb_config['base_url']}/events"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h",  # Simple test with head-to-head
        "oddsFormat": "american"
    }
    
    try:
        response = requests.get(url, params=params)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Games found: {len(data)}")
            if data:
                print(f"First game: {data[0].get('away_team')} @ {data[0].get('home_team')}")
        else:
            print(f"Error: {response.text}")
            
        # Check remaining requests
        remaining = response.headers.get('x-requests-remaining')
        used = response.headers.get('x-requests-used')
        print(f"\nAPI Usage: {used} used, {remaining} remaining")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()