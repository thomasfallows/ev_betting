import pymysql
from decimal import Decimal
import sys
import os
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT, MARKET_MAP

# Splash Sports implied probability (approximately 57.7%)
SPLASH_IMPLIED_PROB = Decimal(1/3)**(Decimal(1/2))

def american_to_prob(odds):
    """Convert American odds to probability"""
    if odds is None: 
        return None
    try:
        odds = Decimal(str(odds))
        if odds < 0:
            return abs(odds) / (abs(odds) + 100)
        else:
            return 100 / (odds + 100)
    except Exception as e:
        logger.error(f"Error converting odds {odds}: {e}")
        return None

def calculate_devigged_probability(books_data):
    """
    Calculate de-vigged probability for props with both sides
    Returns: (true_over_prob, true_under_prob, has_both_sides)
    """
    # Group odds by book
    book_odds = {}
    
    for book, odds, ou in books_data:
        if book not in book_odds:
            book_odds[book] = {}
        book_odds[book][ou] = odds
    
    # Find books with both sides and calculate de-vigged probabilities
    valid_book_probs = []
    
    for book, odds in book_odds.items():
        if 'O' in odds and 'U' in odds:
            over_prob = american_to_prob(odds['O'])
            under_prob = american_to_prob(odds['U'])
            
            if over_prob is None or under_prob is None:
                continue
                
            # Calculate total (includes vig)
            total = over_prob + under_prob
            
            # De-vigged probabilities
            true_over_prob = over_prob / total
            true_under_prob = under_prob / total
            
            valid_book_probs.append({
                'book': book,
                'over_prob': true_over_prob,
                'under_prob': true_under_prob,
                'total_vig': total - 1
            })
    
    if not valid_book_probs:
        return None, None, False
    
    # Average de-vigged probabilities across all valid books
    avg_over_prob = sum(b['over_prob'] for b in valid_book_probs) / len(valid_book_probs)
    avg_under_prob = sum(b['under_prob'] for b in valid_book_probs) / len(valid_book_probs)
    
    return avg_over_prob, avg_under_prob, True

def run_create_report_script():
    """Main function to create EV report with proper de-vigging"""
    logger.info("[Report] Starting EV report generation with de-vigging...")
    logger.info(f"[Report] Splash implied probability: {float(SPLASH_IMPLIED_PROB):.4f}")
    
    conn = None
    try:
        # Connect to database
        conn = pymysql.connect(**DB_CONFIG_DICT)
        with conn.cursor() as cursor:
            logger.info("[Report] Connected to database")
            
            # Truncate existing report
            logger.info("[Report] Truncating table ev_opportunities...")
            cursor.execute("TRUNCATE TABLE ev_opportunities")
            
            # Check data availability
            cursor.execute("SELECT COUNT(*) as count FROM splash_props")
            splash_count = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM player_props")
            player_count = cursor.fetchone()['count']
            logger.info(f"[Report] Found {splash_count} Splash props and {player_count} sportsbook props")
            
            if splash_count == 0 or player_count == 0:
                logger.warning("[Report] No data to process. Run data collection scripts first.")
                return

            # Check if splash_props has sport column
            cursor.execute("SHOW COLUMNS FROM splash_props LIKE 'sport'")
            has_sport_column = cursor.fetchone() is not None
            
            # Build sport selection based on column existence
            sport_select = "sp.sport" if has_sport_column else "'mlb' as sport"

            # Get all props with BOTH sides from the same book
            sql_query = f"""
            SELECT 
                sp.player_name,
                sp.market as splash_market,
                sp.line,
                pp.book,
                pp.ou,
                pp.dxodds,
                pp.home,
                pp.away,
                {sport_select}
            FROM splash_props sp
            JOIN player_props pp ON (
                sp.normalized_name = pp.normalized_name
                AND sp.line = pp.line
                AND pp.market = (CASE sp.market 
                    -- MLB Markets
                    WHEN 'pitcher_ks' THEN 'pitcher_strikeouts'
                    WHEN 'strikeouts' THEN 'pitcher_strikeouts'
                    WHEN 'earned_runs' THEN 'pitcher_earned_runs'
                    WHEN 'allowed_hits' THEN 'pitcher_hits_allowed'
                    WHEN 'hits_allowed' THEN 'pitcher_hits_allowed'
                    WHEN 'total_bases' THEN 'batter_total_bases'
                    WHEN 'hits' THEN 'batter_hits'
                    WHEN 'singles' THEN 'batter_singles'
                    WHEN 'runs' THEN 'batter_runs_scored'
                    WHEN 'rbis' THEN 'batter_rbis'
                    WHEN 'outs' THEN 'pitcher_outs'
                    WHEN 'total_outs' THEN 'pitcher_outs'
                    -- WNBA Markets
                    WHEN 'points' THEN 'player_points'
                    WHEN 'rebounds' THEN 'player_rebounds'
                    WHEN 'pts+reb+asts' THEN 'player_points_rebounds_assists'
                    WHEN 'pts+reb' THEN 'player_points_rebounds'
                    WHEN 'pts+asts' THEN 'player_points_assists'
                    ELSE 'no_match'
                END)
                AND ABS(DATEDIFF(sp.game_date, pp.gamedate)) <= 1
            )
            WHERE pp.dxodds IS NOT NULL
            ORDER BY sp.player_name, sp.market, sp.line, pp.book, pp.ou
            """
            
            logger.info("[Report] Finding props with both sides...")
            cursor.execute(sql_query)
            all_matches = cursor.fetchall()
            
            if not all_matches:
                logger.warning("[Report] No matches found between Splash and sportsbook props!")
                return
            
            # Group props by player/market/line
            props_grouped = {}
            for match in all_matches:
                key = (match['player_name'], match['splash_market'], match['line'])
                if key not in props_grouped:
                    props_grouped[key] = {
                        'home': match['home'],
                        'away': match['away'],
                        'sport': match.get('sport', 'mlb'),
                        'books_data': []
                    }
                props_grouped[key]['books_data'].append((match['book'], match['dxodds'], match['ou']))
            
            logger.info(f"[Report] Found {len(props_grouped)} unique props to analyze")
            
            # Process each prop
            report_rows = []
            one_sided_count = 0
            
            for (player_name, market, line), prop_data in props_grouped.items():
                # Calculate de-vigged probability
                over_prob, under_prob, has_both_sides = calculate_devigged_probability(prop_data['books_data'])
                
                if not has_both_sides:
                    one_sided_count += 1
                    continue
                
                # Calculate EV for both sides
                for side, true_prob in [('O', over_prob), ('U', under_prob)]:
                    ev_percentage = (true_prob - SPLASH_IMPLIED_PROB) * 100
                    
                    # Count books that have this prop
                    book_count = len(set(book for book, _, _ in prop_data['books_data']))
                    
                    # Log positive EV opportunities
                    if ev_percentage > 0:
                        logger.info(f"[Report] POSITIVE EV: {player_name} ({prop_data['sport'].upper()}) {market} {side} {line} - EV: {float(ev_percentage):.2f}% (de-vigged)")
                    
                    # Check if ev_opportunities table has league column
                    cursor.execute("SHOW COLUMNS FROM ev_opportunities LIKE 'league'")
                    has_league_column = cursor.fetchone() is not None
                    
                    if has_league_column:
                        report_rows.append((
                            player_name,
                            side,
                            market,
                            prop_data['home'],
                            prop_data['away'],
                            float(line),
                            float(ev_percentage),
                            book_count,
                            prop_data['sport']
                        ))
                    else:
                        report_rows.append((
                            player_name,
                            side,
                            market,
                            prop_data['home'],
                            prop_data['away'],
                            float(line),
                            float(ev_percentage),
                            book_count
                        ))
            
            logger.info(f"[Report] Skipped {one_sided_count} one-sided props")
            
            # Insert results
            if report_rows:
                logger.info(f"[Report] Inserting {len(report_rows)} EV calculations...")
                
                # Check if we have league column
                cursor.execute("SHOW COLUMNS FROM ev_opportunities LIKE 'league'")
                has_league_column = cursor.fetchone() is not None
                
                if has_league_column:
                    insert_sql = """INSERT INTO ev_opportunities 
                                   (player_name, ou, market_type, home_team, away_team, line, ev_percentage, book_count, league) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                else:
                    insert_sql = """INSERT INTO ev_opportunities 
                                   (player_name, ou, market_type, home_team, away_team, line, ev_percentage, book_count) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
                
                cursor.executemany(insert_sql, report_rows)
                conn.commit()
                
                positive_count = len([row for row in report_rows if row[6] > 0])
                logger.info(f"[Report] Successfully inserted {len(report_rows)} records")
                logger.info(f"[Report] Found {positive_count} positive EV opportunities (with proper de-vigging)")
                
                # Show top opportunities
                if has_league_column:
                    cursor.execute("""
                        SELECT player_name, market_type, ou, line, ev_percentage, book_count, league
                        FROM ev_opportunities
                        ORDER BY ev_percentage DESC
                        LIMIT 5
                    """)
                else:
                    cursor.execute("""
                        SELECT player_name, market_type, ou, line, ev_percentage, book_count
                        FROM ev_opportunities
                        ORDER BY ev_percentage DESC
                        LIMIT 5
                    """)
                    
                top_evs = cursor.fetchall()
                logger.info("[Report] Top 5 EV opportunities (de-vigged):")
                for ev in top_evs:
                    league_info = f" ({ev.get('league', 'N/A').upper()})" if 'league' in ev else ""
                    logger.info(f"  {ev['player_name']}{league_info} {ev['market_type']} {ev['ou']} {ev['line']} - EV: {ev['ev_percentage']:.2f}% ({ev['book_count']} books)")
            else:
                logger.warning("[Report] No EV opportunities calculated")
                
    except pymysql.Error as e:
        logger.error(f"[Report] Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[Report] Unexpected error: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("[Report] Database connection closed")

if __name__ == "__main__":
    print("Running Create Report script with de-vigging...")
    run_create_report_script()
    print("Create Report script finished.")