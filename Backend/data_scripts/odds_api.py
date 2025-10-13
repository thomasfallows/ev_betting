import requests
import pymysql
from datetime import datetime, timedelta
import pytz
import sys
import os
import re
import unicodedata
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    API_KEY, DB_CONFIG, SPORTS_CONFIG, REGION, US_ONLY, 
    US_KEYWORDS, LOCAL_TZ_STR, MARKET_MAP
)

# API rate limiting
API_CALLS_MADE = 0
API_TOKENS_USED = 0
API_DELAY = 0.5  # Delay between API calls in seconds

def calculate_token_cost(markets_count, regions_count):
    """Calculate API token cost based on pricing model"""
    return markets_count * regions_count * 10

def normalize_player_name(name):
    """Normalize player names for consistent database storage"""
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

def american_to_decimal(american_odds):
    """Convert American odds to decimal odds"""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def calculate_football_position(api_position, market, line):
    """
    Calculate football position (QB, WR1, WR2, WR3, TE, RB) based on market and line

    Args:
        api_position: Position from API (if available) - e.g., 'QB', 'WR', 'TE', 'RB'
        market: Market type (e.g., 'player_pass_yds', 'player_reception_yds')
        line: Line value (e.g., 285.5, 65.5)

    Returns:
        str: Position (QB, WR1, WR2, WR3, TE, RB) or None
    """
    # QB: Pass yards or pass completions markets
    if market in ['player_pass_yds', 'player_pass_completions']:
        return 'QB'

    # For receiving markets, determine WR tier based on line
    if market in ['player_reception_yds']:
        if api_position:
            # If API provides position, use it with line-based granularity
            if 'TE' in api_position.upper():
                return 'TE'
            elif 'RB' in api_position.upper():
                return 'RB'
            elif 'WR' in api_position.upper() or 'WIDE' in api_position.upper():
                # Determine WR tier based on receiving yards line
                if line >= 60:
                    return 'WR1'
                elif line >= 40:
                    return 'WR2'
                else:
                    return 'WR3'
        else:
            # No position from API - infer from line only (receiving yards)
            if line >= 60:
                return 'WR1'  # Could be top WR or TE
            elif line >= 40:
                return 'WR2'
            else:
                return 'WR3'

    # For receptions market, use different thresholds
    if market == 'player_receptions':
        if api_position:
            # If API provides position, use it with line-based granularity
            if 'TE' in api_position.upper():
                return 'TE'
            elif 'RB' in api_position.upper():
                return 'RB'
            elif 'WR' in api_position.upper() or 'WIDE' in api_position.upper():
                # For receptions, use different thresholds than yards
                if line >= 6:
                    return 'WR1'
                elif line >= 4:
                    return 'WR2'
                else:
                    return 'WR3'
        else:
            # No position from API - infer from line only (receptions)
            if line >= 6:
                return 'WR1'
            elif line >= 4:
                return 'WR2'
            else:
                return 'WR3'

    return None

def fetch_game_odds(game_id, sport_key):
    """Fetch player prop odds for a specific game"""
    global API_CALLS_MADE, API_TOKENS_USED
    
    try:
        # Use the sport-specific configuration
        sport_config = SPORTS_CONFIG.get(sport_key)
        if not sport_config:
            logger.error(f"[Odds-API] No configuration found for sport: {sport_key}")
            return []
        
        base_url = sport_config['base_url']
        markets = sport_config['markets']
        
        # Calculate token cost
        markets_count = len(markets.split(','))
        regions_count = len(REGION.split(','))
        token_cost = calculate_token_cost(markets_count, regions_count)
        
        url = f"{base_url}/events/{game_id}/odds"
        params = {
            "apiKey": API_KEY,
            "regions": REGION,
            "markets": markets,
            "oddsFormat": "american"
        }
        
        logger.info(f"[Odds-API] Fetching odds for game {game_id} ({sport_key.upper()})...")
        
        # Add delay between API calls
        time.sleep(API_DELAY)
        
        response = requests.get(url, params=params)
        API_CALLS_MADE += 1
        API_TOKENS_USED += token_cost
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"[Odds-API] Failed to fetch odds for game {game_id}: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"[Odds-API] Error fetching odds for game {game_id}: {e}")
        return []

def get_splash_props_from_db(sports_filter=None):
    """
    Get all unique props from splash_props table

    Args:
        sports_filter: List of sport keys to filter (e.g., ['mlb', 'nfl']), or None for all
    """
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cursor:
            # Check if sport column exists
            cursor.execute("SHOW COLUMNS FROM splash_props LIKE 'sport'")
            has_sport_column = cursor.fetchone() is not None

            if has_sport_column:
                # Get props, optionally filtered by sport
                if sports_filter:
                    placeholders = ','.join(['%s'] * len(sports_filter))
                    cursor.execute(f"""
                        SELECT DISTINCT normalized_name, market, line, sport
                        FROM splash_props
                        WHERE sport IN ({placeholders})
                        ORDER BY sport, normalized_name, market, line
                    """, sports_filter)
                else:
                    cursor.execute("""
                        SELECT DISTINCT normalized_name, market, line, sport
                        FROM splash_props
                        ORDER BY sport, normalized_name, market, line
                    """)
            else:
                # Assume all props are MLB if no sport column
                cursor.execute("""
                    SELECT DISTINCT normalized_name, market, line, 'mlb' as sport
                    FROM splash_props
                    ORDER BY normalized_name, market, line
                """)

            props = cursor.fetchall()

            # Count by sport
            sport_counts = {}
            for prop in props:
                sport = prop[3]
                sport_counts[sport] = sport_counts.get(sport, 0) + 1

            logger.info(f"[Odds-API] Found {len(props)} unique props from Splash")
            for sport, count in sport_counts.items():
                logger.info(f"[Odds-API]   {sport.upper()}: {count} props")

            return props
    finally:
        conn.close()

def run_splash_driven_odds_collection(sports_filter=None):
    """
    Main function to collect odds data based on Splash props

    Args:
        sports_filter: List of sport keys to fetch (e.g., ['mlb', 'nfl']), or None for all sports
    """
    global API_CALLS_MADE, API_TOKENS_USED
    API_CALLS_MADE = 0
    API_TOKENS_USED = 0

    if sports_filter:
        logger.info(f"[Odds-API] Starting odds collection for: {', '.join(sports_filter).upper()}")
    else:
        logger.info("[Odds-API] Starting Splash-driven odds collection (all sports)...")

    # Initialize result dictionary
    result = {
        'success': False,
        'api_calls': 0,
        'tokens_used': 0,
        'props_inserted': 0,
        'error': None
    }

    if not API_KEY:
        logger.error("[Odds-API] No API key found! Please set ODDS_API_KEY in your .env file")
        result['error'] = "No API key found! Please set ODDS_API_KEY in your .env file"
        return result

    conn = None
    try:
        # Get Splash props with optional sport filter
        splash_props = get_splash_props_from_db(sports_filter=sports_filter)
        if not splash_props:
            logger.warning("[Odds-API] No Splash props found. Run splash_scraper first.")
            result['error'] = "No Splash props found. Run splash_scraper first."
            return result

        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # Determine which sports to fetch
            sports_to_fetch = {k: v for k, v in SPORTS_CONFIG.items()
                             if not sports_filter or k in sports_filter}

            if not sports_to_fetch:
                logger.warning(f"[Odds-API] No valid sports found in filter: {sports_filter}")
                result['error'] = f"No valid sports found in filter: {sports_filter}"
                return result

            # Delete existing data for sports being fetched
            if sports_filter:
                placeholders = ','.join(['%s'] * len(sports_filter))
                logger.info(f"[Odds-API] Deleting existing data for: {', '.join(sports_filter).upper()}")
                cursor.execute(f"DELETE FROM player_props WHERE sport IN ({placeholders})", sports_filter)
            else:
                logger.info("[Odds-API] Truncating player_props table...")
                cursor.execute("TRUNCATE TABLE player_props")

            # Get all available games for each sport
            games_by_sport = {}

            for sport_key in sports_to_fetch.keys():
                logger.info(f"[Odds-API] Fetching {sport_key.upper()} games...")
                
                sport_config = SPORTS_CONFIG[sport_key]
                url = f"{sport_config['base_url']}/events"
                params = {
                    "apiKey": API_KEY,
                    "regions": REGION,
                    "markets": sport_config['markets'],
                    "oddsFormat": "american"
                }
                
                # Calculate token cost for game list
                markets_count = len(sport_config['markets'].split(','))
                regions_count = len(REGION.split(','))
                token_cost = calculate_token_cost(markets_count, regions_count)
                
                time.sleep(API_DELAY)
                response = requests.get(url, params=params)
                API_CALLS_MADE += 1
                API_TOKENS_USED += token_cost
                
                if response.status_code == 200:
                    games = response.json()
                    games_by_sport[sport_key] = games
                    logger.info(f"[Odds-API] Found {len(games)} {sport_key.upper()} games")
                else:
                    logger.error(f"[Odds-API] Failed to fetch {sport_key.upper()} games: {response.status_code}")
                    games_by_sport[sport_key] = []
            
            # Process each game
            all_props_to_insert = []
            total_games = sum(len(games) for games in games_by_sport.values())
            
            for sport_key, games in games_by_sport.items():
                logger.info(f"[Odds-API] Processing {len(games)} {sport_key.upper()} games...")
                
                for idx, game in enumerate(games):
                    game_id = game.get('id')
                    home_team = game.get('home_team')
                    away_team = game.get('away_team')
                    commence_time = game.get('commence_time')
                    
                    if commence_time:
                        game_date = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                    else:
                        game_date = datetime.now()
                    
                    logger.info(f"[Odds-API] [{idx+1}/{len(games)}] Processing {away_team} @ {home_team} ({sport_key.upper()})...")
                    
                    # Get odds for this game
                    game_data = fetch_game_odds(game_id, sport_key)
                    
                    if not game_data:
                        continue
                    
                    # Process each bookmaker
                    bookmakers = game_data.get('bookmakers', [])
                    
                    for book in bookmakers:
                        book_key = book.get('key', '')
                        book_title = book.get('title', '')
                        
                        # Skip non-US books if US_ONLY is True
                        if US_ONLY and not any(keyword in book_key.lower() for keyword in US_KEYWORDS):
                            continue
                        
                        # Process each market
                        markets = book.get('markets', [])
                        
                        for market in markets:
                            market_key = market.get('key')
                            
                            # Process outcomes
                            outcomes = market.get('outcomes', [])
                            
                            for outcome in outcomes:
                                player_name = outcome.get('description', outcome.get('name', ''))

                                # Skip if this looks like a team total
                                if any(word in player_name.lower() for word in ['team', 'total', home_team.lower(), away_team.lower()]):
                                    continue

                                # Normalize player name
                                normalized_name = normalize_player_name(player_name)

                                # Extract position from outcome if available (for football)
                                position = None
                                if sport_key in ['nfl', 'ncaaf']:
                                    position = outcome.get('position', None)  # Some APIs provide position

                                # Get the point/line
                                point = outcome.get('point')
                                if point is None:
                                    continue
                                
                                # Determine over/under
                                outcome_name = outcome.get('name', '').lower()
                                if 'over' in outcome_name:
                                    ou = 'O'
                                elif 'under' in outcome_name:
                                    ou = 'U'
                                else:
                                    continue
                                
                                # Get odds
                                price = outcome.get('price')
                                if price is None:
                                    continue
                                
                                # Convert to decimal odds
                                decimal_odds = american_to_decimal(price)

                                # Check if this prop matches any Splash prop
                                splash_market = None
                                for splash_prop in splash_props:
                                    splash_norm_name, splash_mkt, splash_line, splash_sport = splash_prop

                                    # Check if sport matches
                                    if splash_sport != sport_key:
                                        continue

                                    # Determine line tolerance based on sport
                                    # Football: ±1.6 (books use different lines)
                                    # MLB/WNBA: ±0.01 (exact match - books agree on lines)
                                    if sport_key in ['nfl', 'ncaaf']:
                                        line_tolerance = 1.6
                                    else:
                                        line_tolerance = 0.01

                                    # Check if player and line match
                                    if (splash_norm_name == normalized_name and
                                        abs(float(splash_line) - float(point)) <= line_tolerance):

                                        # Map Splash market to API market
                                        api_market = MARKET_MAP.get(splash_mkt, splash_mkt)
                                        if api_market == market_key:
                                            splash_market = splash_mkt
                                            break

                                # Only insert if this matches a Splash prop
                                if splash_market:
                                    # Calculate football position if needed (WR1/WR2/WR3/TE/RB/QB)
                                    position_football = None
                                    if sport_key in ['nfl', 'ncaaf']:
                                        position_football = calculate_football_position(
                                            position, market_key, point
                                        )

                                    prop_tuple = (
                                        game_id,            # event_id
                                        sport_key,          # sport
                                        sport_key.upper(),  # league
                                        game_date,          # gamedate
                                        home_team,          # home
                                        away_team,          # away
                                        book_title,         # book
                                        market_key,         # market
                                        player_name,        # Player
                                        normalized_name,    # normalized_name
                                        point,              # line
                                        ou,                 # ou
                                        price,              # dxodds
                                        decimal_odds,       # prob
                                        datetime.now(),     # refreshed
                                        position_football   # position_football
                                    )
                                    all_props_to_insert.append(prop_tuple)
            
            # Insert all props
            if all_props_to_insert:
                logger.info(f"[Odds-API] Inserting {len(all_props_to_insert)} matched props...")
                
                sql = """INSERT IGNORE INTO player_props
                        (event_id, sport, league, gamedate, home, away, book, market,
                         Player, normalized_name, line, ou, dxodds, prob, refreshed, position_football)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                
                cursor.executemany(sql, all_props_to_insert)
                conn.commit()
                
                # Show summary by book
                book_counts = {}
                for prop in all_props_to_insert:
                    book = prop[6]  # book is now at index 6
                    book_counts[book] = book_counts.get(book, 0) + 1
                
                logger.info("[Odds-API] Props by sportsbook:")
                for book, count in sorted(book_counts.items()):
                    logger.info(f"  {book}: {count} props")
            else:
                logger.warning("[Odds-API] No matching props found between Splash and sportsbooks")
            
            logger.info(f"[Odds-API] Total API calls made: {API_CALLS_MADE}")
            logger.info(f"[Odds-API] Total tokens used: {API_TOKENS_USED}")
            
            # Update result
            result['success'] = True
            result['api_calls'] = API_CALLS_MADE
            result['tokens_used'] = API_TOKENS_USED
            result['props_inserted'] = len(all_props_to_insert)
            
    except pymysql.Error as e:
        logger.error(f"[Odds-API] Database error: {e}")
        result['error'] = f"Database error: {e}"
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[Odds-API] Unexpected error: {e}", exc_info=True)
        result['error'] = f"Unexpected error: {e}"
    finally:
        if conn:
            conn.close()
            logger.info("[Odds-API] Database connection closed")
    
    return result

if __name__ == "__main__":
    import sys

    # Check for sport filter argument
    if len(sys.argv) > 1:
        sports_filter = [s.lower() for s in sys.argv[1:]]
        print(f"Running Odds Collection for: {', '.join(sports_filter).upper()}...")
        result = run_splash_driven_odds_collection(sports_filter=sports_filter)
    else:
        print("Running Splash-driven Odds Collection script (all sports)...")
        result = run_splash_driven_odds_collection()

    print("Odds collection script finished.")
    if result.get('success'):
        print(f"✓ Inserted {result['props_inserted']} props")
        print(f"✓ API calls: {result['api_calls']}, Tokens used: {result['tokens_used']}")
    else:
        print(f"✗ Error: {result.get('error', 'Unknown error')}")