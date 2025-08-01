import requests
import pymysql
from datetime import datetime
import sys
import os
import logging
import unicodedata
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

# Splash API configuration - supports multiple sports
API_CONFIG = {
    'mlb': {
        'url': "https://api.splashsports.com/props-service/api/props",
        'params': {"league": "mlb"}
    },
    'wnba': {
        'url': "https://api.splashsports.com/props-service/api/props", 
        'params': {"league": "wnba"}
    }
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
}

def normalize_player_name(name):
    """Normalize player names for database storage"""
    if not name:
        return ""
    
    # Remove accents and special characters
    name = unicodedata.normalize('NFD', name)
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    
    # Clean up the name
    name = re.sub(r'[^\w\s.-]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()
    
    return name

def scrape_sport_props(sport_key, sport_config):
    """Scrape props for a specific sport from Splash"""
    logger.info(f"[Splash-{sport_key.upper()}] Fetching props...")
    
    # Setup session for connection reuse
    session = requests.Session()
    session.headers.update(HEADERS)
    
    offset, limit = 0, 100
    total_props = -1
    all_props_to_insert = []
    
    while True:
        params = sport_config['params'].copy()
        params.update({
            "limit": limit,
            "offset": offset
        })
        
        try:
            response = session.get(sport_config['url'], params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"[Splash-{sport_key.upper()}] Failed to fetch data at offset {offset}: {e}")
            break
        except ValueError as e:
            logger.error(f"[Splash-{sport_key.upper()}] Invalid JSON response: {e}")
            break
        
        # Extract props from response
        props = data.get("data", [])
        
        if not props:
            logger.info(f"[Splash-{sport_key.upper()}] No more props to fetch")
            break
        
        # Get total count on first iteration
        if total_props == -1:
            total_props = data.get("total", 0)
            logger.info(f"[Splash-{sport_key.upper()}] Total props available: {total_props}")
        
        # Process each prop
        for prop in props:
            try:
                # Extract fields with validation
                player_name = prop.get("entity_name")
                if not player_name:
                    logger.warning(f"[Splash-{sport_key.upper()}] Prop missing player name, skipping")
                    continue
                
                # Team info (might be different structure for WNBA)
                team_info = prop.get("team", {})
                team_abbr = team_info.get("alias") if isinstance(team_info, dict) else None
                
                # Market type (confusingly called "type" in their API)
                market_type = prop.get("type")
                if not market_type:
                    logger.warning(f"[Splash-{sport_key.upper()}] Prop for {player_name} missing market type, skipping")
                    continue
                
                # Line value
                line = prop.get("line")
                if line is None:
                    logger.warning(f"[Splash-{sport_key.upper()}] Prop for {player_name} missing line value, skipping")
                    continue
                
                # Game start time
                game_start_ms = prop.get("game_start", 0)
                if game_start_ms <= 0:
                    logger.warning(f"[Splash-{sport_key.upper()}] Invalid game start time for {player_name}")
                    game_date = datetime.now()
                else:
                    try:
                        game_date = datetime.fromtimestamp(game_start_ms / 1000)
                    except (ValueError, OSError) as e:
                        logger.error(f"[Splash-{sport_key.upper()}] Error parsing timestamp {game_start_ms}: {e}")
                        game_date = datetime.now()
                
                # Normalize player name
                normalized_name = normalize_player_name(player_name)
                
                # Create tuple for insertion
                prop_tuple = (
                    player_name,
                    normalized_name,
                    team_abbr,
                    market_type,  # This is their market name
                    line,
                    game_date,
                    sport_key,   # Store sport type
                    datetime.now()  # last_updated
                )
                
                all_props_to_insert.append(prop_tuple)
                
            except Exception as e:
                logger.error(f"[Splash-{sport_key.upper()}] Error processing prop: {e}", exc_info=True)
                continue
        
        logger.info(f"[Splash-{sport_key.upper()}] Processed {len(props)} props at offset {offset}")
        
        # Update offset for next page
        offset += limit
        
        # Check if we've fetched all props
        if total_props != -1 and offset >= total_props:
            logger.info(f"[Splash-{sport_key.upper()}] Reached end of available props")
            break
    
    logger.info(f"[Splash-{sport_key.upper()}] Fetched {len(all_props_to_insert)} total props")
    return all_props_to_insert

def run_splash_scraper_script():
    """Main function to scrape props from Splash Sports for all supported sports"""
    logger.info("[Splash] Starting multi-sport Splash Sports scraper...")
    
    conn = None
    try:
        # Connect to database
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            logger.info("[Splash] Connected to database")
            
            # Truncate existing data
            logger.info("[Splash] Truncating table splash_props...")
            cursor.execute("TRUNCATE TABLE splash_props")
            
            all_props_combined = []
            
            # Scrape each sport
            for sport_key, sport_config in API_CONFIG.items():
                sport_props = scrape_sport_props(sport_key, sport_config)
                all_props_combined.extend(sport_props)
            
            # De-duplicate and insert
            if all_props_combined:
                logger.info(f"[Splash] Fetched {len(all_props_combined)} total props across all sports")
                
                # De-duplicate based on database precision
                # Key: (player_name, market, line, game_date without microseconds, sport)
                unique_props_dict = {}
                
                for prop_tuple in all_props_combined:
                    player_name = prop_tuple[0]
                    market = prop_tuple[3]
                    line = prop_tuple[4]
                    game_date_no_ms = prop_tuple[5].replace(microsecond=0)
                    sport = prop_tuple[6]
                    
                    # Create unique key
                    key = (player_name, market, line, game_date_no_ms, sport)
                    
                    # Keep first occurrence
                    if key not in unique_props_dict:
                        unique_props_dict[key] = prop_tuple
                
                unique_props = list(unique_props_dict.values())
                logger.info(f"[Splash] After de-duplication: {len(unique_props)} unique props")
                
                # Insert into database
                sql = """INSERT INTO splash_props 
                        (player_name, normalized_name, team_abbr, market, line, game_date, sport, last_updated) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                
                cursor.executemany(sql, unique_props)
                conn.commit()
                logger.info("[Splash] Data insertion complete")
                
                # Show breakdown by sport
                cursor.execute("""
                    SELECT sport, COUNT(*) as count 
                    FROM splash_props 
                    GROUP BY sport 
                    ORDER BY count DESC
                """)
                sport_breakdown = cursor.fetchall()
                logger.info("[Splash] Props by sport:")
                for row in sport_breakdown:
                    logger.info(f"  {row[0].upper()}: {row[1]} props")
                
            else:
                logger.warning("[Splash] No props found to insert")
    
    except pymysql.Error as e:
        logger.error(f"[Splash] Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[Splash] Unexpected error: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("[Splash] Database connection closed")

if __name__ == "__main__":
    print("Running Multi-Sport Splash Scraper script...")
    run_splash_scraper_script()
    print("Multi-Sport Splash Scraper script finished.")