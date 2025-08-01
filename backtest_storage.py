"""
Historical Odds Collection Script
Fetches and stores historical odds data from The Odds API
"""

import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
import os
import pymysql
from typing import Dict, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
ODDS_API_KEY = os.environ.get('ODDS_API_KEY', 'YOUR_API_KEY_HERE')
DB_CONFIG = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'database': 'betting_odds',
    'charset': 'utf8mb4'
}

# Books configuration
SHARP_BOOKS = ['pinnacle', 'bet365', 'betfair', 'bookmaker']
SOFT_BOOKS = ['draftkings', 'fanduel', 'betmgm', 'caesars']
ALL_BOOKS = SHARP_BOOKS + SOFT_BOOKS

class HistoricalOddsDatabase:
    """
    Manages storage of historical odds data
    """
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.connection = None
        self.cursor = None
        
    def connect(self):
        """Establish database connection"""
        self.connection = pymysql.connect(**self.db_config)
        self.cursor = self.connection.cursor()
        
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        
        # Historical odds table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_odds (
            id INT AUTO_INCREMENT PRIMARY KEY,
            fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            game_date DATE NOT NULL,
            sport VARCHAR(50),
            game_id VARCHAR(100),
            player_name VARCHAR(100),
            player_clean VARCHAR(100),
            market_type VARCHAR(50),
            market_standard VARCHAR(50),
            line DECIMAL(10,2),
            side VARCHAR(10),
            bookmaker VARCHAR(50),
            odds INT,
            true_probability DECIMAL(5,4),
            ev_percentage DECIMAL(10,2),
            INDEX idx_date_player (game_date, player_clean),
            INDEX idx_market (market_standard),
            INDEX idx_book (bookmaker),
            UNIQUE KEY unique_prop (game_date, player_clean, market_standard, line, side, bookmaker)
        )
        """)
        
        # API usage tracking
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INT AUTO_INCREMENT PRIMARY KEY,
            request_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            endpoint VARCHAR(200),
            requests_used INT,
            requests_remaining INT
        )
        """)
        
        self.connection.commit()
        logger.info("Database tables created/verified")

class OddsAPICollector:
    """
    Collects odds data from The Odds API
    """
    
    def __init__(self, api_key: str, db: HistoricalOddsDatabase):
        self.api_key = api_key
        self.db = db
        self.base_url = "https://api.the-odds-api.com/v4"
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Historical Odds Collector'})
        
    def check_api_usage(self, response):
        """Track API usage from response headers"""
        requests_used = response.headers.get('x-requests-used', 0)
        requests_remaining = response.headers.get('x-requests-remaining', 0)
        
        logger.info(f"API Usage - Used: {requests_used}, Remaining: {requests_remaining}")
        
        # Store in database
        self.db.cursor.execute("""
        INSERT INTO api_usage (endpoint, requests_used, requests_remaining)
        VALUES (%s, %s, %s)
        """, (response.url, requests_used, requests_remaining))
        self.db.connection.commit()
        
        return int(requests_remaining)
    
    def get_sports_odds(self, sport: str, date: datetime) -> List[Dict]:
        """
        Get odds for all games on a specific date
        """
        # Format date for API
        date_str = date.strftime('%Y-%m-%dT00:00:00Z')
        
        # Construct request
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': 'us',
            'markets': 'player_points,player_rebounds,player_assists,player_threes,player_points_rebounds_assists,player_points_rebounds,player_points_assists,player_rebounds_assists',
            'bookmakers': ','.join(ALL_BOOKS),
            'commenceTimeFrom': date_str,
            'commenceTimeTo': (date + timedelta(days=1)).strftime('%Y-%m-%dT00:00:00Z')
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # Check API usage
            remaining = self.check_api_usage(response)
            
            # Parse response
            data = response.json()
            logger.info(f"Retrieved {len(data)} games for {sport} on {date.date()}")
            
            # Rate limiting
            if remaining < 100:
                logger.warning(f"Low API requests remaining: {remaining}")
                time.sleep(2)  # Slow down
            else:
                time.sleep(0.5)  # Normal rate
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return []
    
    def parse_and_store_odds(self, odds_data: List[Dict], sport: str):
        """
        Parse odds data and store in database
        """
        props_stored = 0
        
        for game in odds_data:
            game_date = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00')).date()
            game_id = game['id']
            
            for bookmaker in game.get('bookmakers', []):
                book_name = bookmaker['key']
                
                for market in bookmaker.get('markets', []):
                    market_type = market['key']
                    
                    # Standardize market names
                    market_standard = self.standardize_market(market_type)
                    
                    for outcome in market.get('outcomes', []):
                        player_name = outcome.get('description', '')
                        
                        # Skip team totals
                        if not player_name or 'Team' in player_name:
                            continue
                        
                        player_clean = self.clean_player_name(player_name)
                        line = outcome.get('point', 0)
                        side = outcome['name'].upper()  # OVER/UNDER
                        odds = outcome['price']
                        
                        # Store in database
                        try:
                            self.db.cursor.execute("""
                            INSERT INTO historical_odds 
                            (game_date, sport, game_id, player_name, player_clean, 
                             market_type, market_standard, line, side, bookmaker, odds)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE odds = VALUES(odds)
                            """, (game_date, sport, game_id, player_name, player_clean,
                                  market_type, market_standard, line, side, book_name, odds))
                            
                            props_stored += 1
                            
                        except Exception as e:
                            logger.error(f"Failed to store prop: {e}")
        
        self.db.connection.commit()
        logger.info(f"Stored {props_stored} prop bets")
        
        return props_stored
    
    def standardize_market(self, market: str) -> str:
        """Standardize market names to match our system"""
        market_map = {
            'player_points': 'points',
            'player_rebounds': 'rebounds',
            'player_assists': 'assists',
            'player_threes': 'threes_made',
            'player_points_rebounds_assists': 'points_rebounds_assists',
            'player_points_rebounds': 'points_rebounds',
            'player_points_assists': 'points_assists',
            'player_rebounds_assists': 'rebounds_assists',
            'player_blocks': 'blocks',
            'player_steals': 'steals',
            'player_turnovers': 'turnovers',
            # Hockey
            'player_goals': 'goals',
            'player_shots_on_goal': 'shots_on_goal',
            'player_blocked_shots': 'blocked_shots',
            'player_saves': 'saves'
        }
        return market_map.get(market, market)
    
    def clean_player_name(self, name: str) -> str:
        """Clean and standardize player names"""
        import re
        
        # Basic cleaning
        name = name.strip()
        name = re.sub(r'\s+', ' ', name)
        
        # Remove team abbreviations if present
        name = re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', name)
        
        # Standardize suffixes
        name = name.replace('Jr.', 'Jr').replace('Sr.', 'Sr')
        
        return name
    
    def collect_date_range(self, start_date: datetime, end_date: datetime, sports: List[str]):
        """
        Collect odds for a date range across multiple sports
        """
        current_date = start_date
        total_props = 0
        
        while current_date <= end_date:
            logger.info(f"\nProcessing {current_date.date()}")
            
            for sport in sports:
                logger.info(f"  Fetching {sport}...")
                odds_data = self.get_sports_odds(sport, current_date)
                
                if odds_data:
                    props = self.parse_and_store_odds(odds_data, sport)
                    total_props += props
            
            current_date += timedelta(days=1)
        
        logger.info(f"\nTotal props collected: {total_props}")
        return total_props

def calculate_historical_evs(db: HistoricalOddsDatabase):
    """
    Calculate EVs for all stored odds using sharp book consensus
    """
    logger.info("Calculating historical EVs...")
    
    # Get all unique prop combinations
    db.cursor.execute("""
    SELECT DISTINCT game_date, player_clean, market_standard, line, side
    FROM historical_odds
    WHERE bookmaker IN (%s)
    """ % ','.join(['%s'] * len(SHARP_BOOKS)), SHARP_BOOKS)
    
    props = db.cursor.fetchall()
    logger.info(f"Found {len(props)} unique props to calculate EVs for")
    
    for prop in props:
        game_date, player, market, line, side = prop
        
        # Get sharp book odds for this prop
        db.cursor.execute("""
        SELECT bookmaker, odds
        FROM historical_odds
        WHERE game_date = %s AND player_clean = %s 
        AND market_standard = %s AND line = %s AND side = %s
        AND bookmaker IN (%s)
        """ % ','.join(['%s'] * len(SHARP_BOOKS)), 
        (game_date, player, market, line, side, *SHARP_BOOKS))
        
        sharp_odds = db.cursor.fetchall()
        
        if sharp_odds:
            # Calculate true probability from sharp books
            odds_values = [odd[1] for odd in sharp_odds]
            true_prob = calculate_true_probability_from_odds(odds_values)
            
            # Update all books with EV calculation
            db.cursor.execute("""
            UPDATE historical_odds
            SET true_probability = %s,
                ev_percentage = calculate_ev(%s, odds)
            WHERE game_date = %s AND player_clean = %s 
            AND market_standard = %s AND line = %s AND side = %s
            """, (true_prob, true_prob, game_date, player, market, line, side))
    
    db.connection.commit()
    logger.info("EV calculations complete")

def calculate_true_probability_from_odds(odds_list: List[int]) -> float:
    """Calculate true probability from list of odds"""
    # Convert American odds to implied probabilities
    implied_probs = []
    for odds in odds_list:
        if odds > 0:
            prob = 100 / (odds + 100)
        else:
            prob = abs(odds) / (abs(odds) + 100)
        implied_probs.append(prob)
    
    # Simple average (more sophisticated devigging could be implemented)
    return sum(implied_probs) / len(implied_probs)

def main():
    """
    Main execution function
    """
    print("="*60)
    print("HISTORICAL ODDS COLLECTION SYSTEM")
    print("="*60)
    
    # Check for API key
    if ODDS_API_KEY == 'YOUR_API_KEY_HERE':
        print("\n❌ Please set your ODDS_API_KEY environment variable")
        print("   Example: set ODDS_API_KEY=your_actual_key_here")
        return
    
    # Initialize database
    db = HistoricalOddsDatabase(DB_CONFIG)
    db.connect()
    db.create_tables()
    
    # Initialize collector
    collector = OddsAPICollector(ODDS_API_KEY, db)
    
    # Define date range to collect
    # You should match this to your historical picks date range
    start_date = datetime(2025, 2, 25)  # Start of your data
    end_date = datetime(2025, 3, 15)    # End of first batch
    
    # Sports to collect
    sports = ['basketball_nba', 'icehockey_nhl']
    
    try:
        # Collect odds data
        print(f"\nCollecting odds from {start_date.date()} to {end_date.date()}")
        print("This may take a while due to rate limits...")
        
        total_props = collector.collect_date_range(start_date, end_date, sports)
        
        # Calculate EVs
        calculate_historical_evs(db)
        
        print(f"\n✅ Collection complete!")
        print(f"   Total props collected: {total_props}")
        
        # Export to CSV for backup
        db.cursor.execute("""
        SELECT * FROM historical_odds
        ORDER BY game_date, player_clean, market_standard
        """)
        
        columns = [desc[0] for desc in db.cursor.description]
        data = db.cursor.fetchall()
        
        odds_df = pd.DataFrame(data, columns=columns)
        odds_df.to_csv('historical_odds_backup.csv', index=False)
        print(f"   Backup saved to: historical_odds_backup.csv")
        
    finally:
        db.close()

if __name__ == "__main__":
    main()