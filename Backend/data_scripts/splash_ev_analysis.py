import pymysql
from decimal import Decimal
import sys
import os
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT, STAR_PLAYERS, MARKET_MAP

# Splash Sports contest structure
SPLASH_IMPLIED_PROB = Decimal(1/3)**(Decimal(1/2))  # ~57.7%
CONTEST_BREAKEVEN = Decimal('0.577')  # Need to win 57.7% to break even

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

def calculate_public_appeal_score(player_name, market_type, line):
    """Calculate how appealing a prop is to the public"""
    score = 0
    
    # Star player bonus
    if any(star in player_name for star in STAR_PLAYERS):
        score += 3
    
    # Popular markets get higher scores
    popular_markets = ['hits', 'strikeouts', 'pitcher_ks', 'points', 'rebounds']
    if any(market in market_type.lower() for market in popular_markets):
        score += 2
    
    # Round number lines are more popular
    if float(line) == int(float(line)):
        score += 1
    
    # Overs are generally more popular than unders
    # (This will be considered in the main analysis)
    
    return score

def calculate_devigged_probability(books_data):
    """
    Calculate de-vigged probability for props with both sides
    Returns: (true_over_prob, true_under_prob, has_both_sides, book_count)
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
        return None, None, False, 0
    
    # Average de-vigged probabilities across all valid books
    avg_over_prob = sum(b['over_prob'] for b in valid_book_probs) / len(valid_book_probs)
    avg_under_prob = sum(b['under_prob'] for b in valid_book_probs) / len(valid_book_probs)
    
    return avg_over_prob, avg_under_prob, True, len(valid_book_probs)

def run_splash_ev_analysis():
    """Analyze Splash props for EV in contest format with proper de-vigging"""
    logger.info("[Splash-EV] Starting Splash EV analysis with de-vigging...")
    
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        with conn.cursor() as cursor:
            logger.info("[Splash-EV] Connected to database")
            
            # Truncate existing analysis
            logger.info("[Splash-EV] Truncating splash_ev_analysis table...")
            cursor.execute("TRUNCATE TABLE splash_ev_analysis")
            
            # Check if tables have required columns
            cursor.execute("SHOW COLUMNS FROM splash_props LIKE 'sport'")
            has_sport_column = cursor.fetchone() is not None
            
            # Build query based on available columns
            if has_sport_column:
                sport_select = "sp.sport"
            else:
                sport_select = "'mlb' as sport"
            
            # Get all props with their odds data
            logger.info("[Splash-EV] Fetching Splash props with all odds data...")
            
            query = f"""
            SELECT 
                sp.player_name,
                sp.market as splash_market,
                sp.line,
                pp.book,
                pp.ou,
                pp.dxodds,
                {sport_select}
            FROM splash_props sp
            LEFT JOIN player_props pp ON (
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
            )
            WHERE pp.dxodds IS NOT NULL
            ORDER BY sp.player_name, sp.market, sp.line, pp.book, pp.ou
            """
            
            cursor.execute(query)
            all_props_data = cursor.fetchall()
            
            # Group props by player/market/line
            props_grouped = {}
            for prop in all_props_data:
                if prop['book'] is None:  # Skip props with no odds data
                    continue
                    
                key = (prop['player_name'], prop['splash_market'], prop['line'])
                if key not in props_grouped:
                    props_grouped[key] = {
                        'sport': prop.get('sport', 'mlb'),
                        'books_data': []
                    }
                props_grouped[key]['books_data'].append((prop['book'], prop['dxodds'], prop['ou']))
            
            logger.info(f"[Splash-EV] Found {len(props_grouped)} unique Splash props")
            
            analysis_results = []
            profitable_count = 0
            one_sided_count = 0
            
            for (player_name, market_type, line), prop_data in props_grouped.items():
                sport = prop_data['sport']
                
                # Calculate public appeal
                appeal_score = calculate_public_appeal_score(player_name, market_type, line)
                
                # Calculate de-vigged probabilities
                over_prob, under_prob, has_both_sides, book_count = calculate_devigged_probability(prop_data['books_data'])
                
                if not has_both_sides:
                    one_sided_count += 1
                    continue
                
                # Process both sides
                for side, true_prob in [('O', over_prob), ('U', under_prob)]:
                    # Adjust appeal for overs (more popular)
                    adjusted_appeal = appeal_score + 1 if side == 'O' else appeal_score
                    
                    # Calculate EV
                    ev_percentage = (true_prob - SPLASH_IMPLIED_PROB) * 100
                    
                    # Determine if profitable
                    # In contests, we need to beat the breakeven more significantly
                    # due to the top-heavy payout structure
                    adjusted_breakeven = CONTEST_BREAKEVEN + (Decimal(adjusted_appeal) * Decimal('0.01'))
                    profitable = true_prob > adjusted_breakeven
                    
                    if profitable:
                        profitable_count += 1
                    
                    # Log high EV opportunities
                    if ev_percentage > 2:
                        logger.info(f"[Splash-EV] High EV: {player_name} ({sport.upper()}) {market_type} {side} {line} - EV: {float(ev_percentage):.2f}% (de-vigged), Appeal: {adjusted_appeal}")
                    
                    # Check if league column exists in target table
                    cursor.execute("SHOW COLUMNS FROM splash_ev_analysis LIKE 'league'")
                    has_league_column = cursor.fetchone() is not None
                    
                    if has_league_column:
                        analysis_results.append((
                            player_name,
                            market_type,
                            side,
                            float(line),
                            sport,  # league
                            sport,  # sport
                            float(ev_percentage),
                            float(true_prob * 100),
                            adjusted_appeal,
                            book_count,
                            float(adjusted_breakeven * 100),
                            1 if profitable else 0,
                            datetime.now()
                        ))
                    else:
                        analysis_results.append((
                            player_name,
                            market_type,
                            side,
                            float(line),
                            float(ev_percentage),
                            float(true_prob * 100),
                            adjusted_appeal,
                            book_count,
                            float(adjusted_breakeven * 100),
                            1 if profitable else 0,
                            datetime.now()
                        ))
            
            logger.info(f"[Splash-EV] Skipped {one_sided_count} one-sided props")
            
            # Insert analysis results
            if analysis_results:
                logger.info(f"[Splash-EV] Inserting {len(analysis_results)} analysis results...")
                
                cursor.execute("SHOW COLUMNS FROM splash_ev_analysis LIKE 'league'")
                has_league_column = cursor.fetchone() is not None
                
                if has_league_column:
                    insert_sql = """
                    INSERT INTO splash_ev_analysis 
                    (player_name, market_type, side, line, league, sport, ev_percentage, 
                     true_probability, public_appeal_score, book_count, 
                     adjusted_breakeven, profitable, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                else:
                    insert_sql = """
                    INSERT INTO splash_ev_analysis 
                    (player_name, market_type, side, line, ev_percentage, 
                     true_probability, public_appeal_score, book_count, 
                     adjusted_breakeven, profitable, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                
                cursor.executemany(insert_sql, analysis_results)
                conn.commit()
                
                logger.info(f"[Splash-EV] Analysis complete!")
                logger.info(f"[Splash-EV] Total props analyzed: {len(analysis_results)}")
                logger.info(f"[Splash-EV] Profitable props: {profitable_count} ({profitable_count/len(analysis_results)*100:.1f}%)")
                logger.info(f"[Splash-EV] One-sided props skipped: {one_sided_count}")
                
                # Show top opportunities
                cursor.execute("""
                    SELECT player_name, market_type, side, line, ev_percentage
                    FROM splash_ev_analysis
                    WHERE profitable = 1
                    ORDER BY ev_percentage DESC
                    LIMIT 5
                """)
                
                top_props = cursor.fetchall()
                if top_props:
                    logger.info("[Splash-EV] Top 5 profitable Splash props (de-vigged):")
                    for prop in top_props:
                        logger.info(f"  {prop['player_name']} {prop['market_type']} {prop['side']} {prop['line']} - EV: {prop['ev_percentage']:.2f}%")
            else:
                logger.warning("[Splash-EV] No props to analyze")
                
    except pymysql.Error as e:
        logger.error(f"[Splash-EV] Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[Splash-EV] Unexpected error: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("[Splash-EV] Database connection closed")

if __name__ == "__main__":
    print("Running Splash EV Analysis with de-vigging...")
    run_splash_ev_analysis()
    print("Splash EV Analysis complete.")