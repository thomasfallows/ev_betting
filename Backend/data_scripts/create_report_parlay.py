import pymysql
from decimal import Decimal
import sys
import os
import logging
from datetime import datetime, timedelta
import hashlib
import itertools

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT, MARKET_MAP
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config'))
from contest_config import CONTEST_CONFIGS, calculate_contest_ev, get_bankroll_recommendation
from data_scripts.parlay_generator import ParlayGenerator

# Splash Sports implied probability (approximately 57.7%)
SPLASH_IMPLIED_PROB = Decimal(1/3)**(Decimal(1/2))

# Default bankroll for recommendations
DEFAULT_BANKROLL = 60

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

def generate_parlay_hash(legs):
    """Generate unique hash for a parlay based on its legs"""
    # Sort legs to ensure consistent hashing
    sorted_legs = sorted(legs, key=lambda x: f"{x['player_name']}_{x['market']}_{x['line']}_{x['ou']}")
    leg_string = "_".join([f"{leg['player_name']}_{leg['market']}_{leg['line']}_{leg['ou']}" for leg in sorted_legs])
    return hashlib.sha256(leg_string.encode()).hexdigest()

def is_valid_parlay(legs):
    """Check if a parlay combination is valid"""
    # Rule 1: No duplicate players in same parlay
    players = [leg['player_name'] for leg in legs]
    if len(players) != len(set(players)):
        return False
    
    # Rule 2: No same game parlays for now (can be relaxed later for correlations)
    games = [(leg['home'], leg['away']) for leg in legs]
    if len(games) != len(set(games)):
        return False
    
    return True

def generate_parlays(available_props, contest_type='2-man', bankroll=60):
    """Generate smart parlay combinations using correlation analysis"""
    # Use the smart parlay generator
    generator = ParlayGenerator(available_props, contest_type, bankroll)
    smart_parlays = generator.generate_smart_parlays(max_results=100)
    
    # Convert to expected format
    valid_parlays = []
    for parlay in smart_parlays:
        parlay_hash = generate_parlay_hash(parlay['legs'])
        valid_parlays.append({
            'hash': parlay_hash,
            'legs': parlay['legs'],
            'contest_type': contest_type,
            'parlay_probability': parlay['metrics']['parlay_probability'],
            'ev_result': parlay['metrics']['ev_result'],
            'correlation_score': parlay['metrics']['avg_correlation'],
            'variance_multiplier': parlay['metrics']['variance_multiplier'],
            'risk_adjusted_score': parlay['metrics']['risk_adjusted_score'],
            'parlay_type': parlay['type']
        })
    
    # Log summary
    correlated = [p for p in smart_parlays if p['type'] == 'correlated']
    independent = [p for p in smart_parlays if p['type'] == 'independent']
    
    logger.info(f"[Parlay] Generated {len(valid_parlays)} smart parlays")
    logger.info(f"[Parlay]   Correlated: {len(correlated)} (negative correlation for variance reduction)")
    logger.info(f"[Parlay]   Independent: {len(independent)} (high probability across games)")
    
    if valid_parlays:
        best_corr = min(p['metrics']['avg_correlation'] for p in smart_parlays)
        best_ev = max(p['metrics']['ev_result']['contest_ev_percent'] for p in smart_parlays)
        logger.info(f"[Parlay]   Best correlation: {best_corr:.2f}")
        logger.info(f"[Parlay]   Best EV: {best_ev:.2f}%")
    
    return valid_parlays

def run_parlay_report():
    """Generate parlay-based EV report"""
    logger.info("[Parlay Report] Starting parlay-based EV report generation...")
    logger.info(f"[Parlay Report] Using bankroll: ${DEFAULT_BANKROLL}")
    
    # Get bankroll recommendations
    bankroll_rec = get_bankroll_recommendation(DEFAULT_BANKROLL)
    logger.info(f"[Parlay Report] Recommended contests: {bankroll_rec['recommended_contests']}")
    
    conn = None
    try:
        # Connect to database
        conn = pymysql.connect(**DB_CONFIG_DICT)
        with conn.cursor() as cursor:
            logger.info("[Parlay Report] Connected to database")
            
            # Clear existing parlay data
            logger.info("[Parlay Report] Clearing existing parlay data...")
            cursor.execute("DELETE FROM parlay_legs")
            cursor.execute("DELETE FROM parlays")
            cursor.execute("TRUNCATE TABLE ev_opportunities")
            
            # Check data availability
            cursor.execute("SELECT COUNT(*) as count FROM splash_props")
            splash_count = cursor.fetchone()['count']
            cursor.execute("SELECT COUNT(*) as count FROM player_props")
            player_count = cursor.fetchone()['count']
            logger.info(f"[Parlay Report] Found {splash_count} Splash props and {player_count} sportsbook props")
            
            if splash_count == 0 or player_count == 0:
                logger.warning("[Parlay Report] No data to process. Run data collection scripts first.")
                return

            # Check if splash_props has sport column
            cursor.execute("SHOW COLUMNS FROM splash_props LIKE 'sport'")
            has_sport_column = cursor.fetchone() is not None
            
            # Build sport selection based on column existence
            sport_select = "sp.sport" if has_sport_column else "'mlb' as sport"

            # Get all props with BOTH sides from the same book (same as original)
            sql_query = f"""
            SELECT 
                sp.player_name,
                sp.normalized_name,
                sp.market as splash_market,
                sp.line,
                pp.book,
                pp.ou,
                pp.dxodds,
                pp.home,
                pp.away,
                NULL as game_id,
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
            
            logger.info("[Parlay Report] Finding props with both sides...")
            cursor.execute(sql_query)
            all_matches = cursor.fetchall()
            
            if not all_matches:
                logger.warning("[Parlay Report] No matches found between Splash and sportsbook props!")
                return
            
            # Group props by player/market/line
            props_grouped = {}
            for match in all_matches:
                key = (match['player_name'], match['normalized_name'], match['splash_market'], match['line'])
                if key not in props_grouped:
                    props_grouped[key] = {
                        'home': match['home'],
                        'away': match['away'],
                        'sport': match.get('sport', 'mlb'),
                        'game_id': match['game_id'],
                        'books_data': []
                    }
                props_grouped[key]['books_data'].append((match['book'], match['dxodds'], match['ou']))
            
            logger.info(f"[Parlay Report] Found {len(props_grouped)} unique props to analyze")
            
            # Process each prop and collect valid ones
            available_props = []
            one_sided_count = 0
            
            for (player_name, normalized_name, market, line), prop_data in props_grouped.items():
                # Calculate de-vigged probability
                over_prob, under_prob, has_both_sides = calculate_devigged_probability(prop_data['books_data'])
                
                if not has_both_sides:
                    one_sided_count += 1
                    continue
                
                # Add both sides as available props
                for side, true_prob in [('O', over_prob), ('U', under_prob)]:
                    available_props.append({
                        'player_name': player_name,
                        'normalized_name': normalized_name,
                        'market': market,
                        'line': line,
                        'ou': side,
                        'true_probability': float(true_prob),
                        'home': prop_data['home'],
                        'away': prop_data['away'],
                        'sport': prop_data['sport'],
                        'game_id': prop_data['game_id']
                    })
            
            logger.info(f"[Parlay Report] Skipped {one_sided_count} one-sided props")
            logger.info(f"[Parlay Report] Found {len(available_props)} valid prop sides for parlay generation")
            
            # Generate parlays for recommended contest types
            all_parlays = []
            for contest_type in bankroll_rec['recommended_contests']:
                parlays = generate_parlays(available_props, contest_type, DEFAULT_BANKROLL)
                all_parlays.extend(parlays)
            
            if not all_parlays:
                logger.warning("[Parlay Report] No valid parlays found!")
                return
            
            # Sort by EV
            all_parlays.sort(key=lambda x: x['ev_result']['contest_ev_percent'], reverse=True)
            
            # Insert top parlays into database
            max_parlays = 100  # Limit to top 100 parlays
            inserted_count = 0
            
            for parlay in all_parlays[:max_parlays]:
                try:
                    # Insert into parlays table
                    cursor.execute("""
                        INSERT INTO parlays (
                            contest_type, parlay_hash, leg_count, parlay_probability,
                            contest_ev_percent, break_even_probability, edge_over_breakeven, meets_minimum
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        parlay['contest_type'],
                        parlay['hash'],
                        len(parlay['legs']),
                        parlay['parlay_probability'],
                        parlay['ev_result']['contest_ev_percent'],
                        parlay['ev_result']['break_even_probability'],
                        parlay['ev_result']['edge_over_breakeven'],
                        parlay['ev_result']['meets_minimum']
                    ))
                    
                    # Insert legs
                    for i, leg in enumerate(parlay['legs']):
                        cursor.execute("""
                            INSERT INTO parlay_legs (
                                parlay_hash, leg_number, player_name, normalized_name,
                                market, line, ou, true_probability, sport, game_id
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            parlay['hash'],
                            i + 1,
                            leg['player_name'],
                            leg['normalized_name'],
                            leg['market'],
                            leg['line'],
                            leg['ou'],
                            leg['true_probability'],
                            leg['sport'],
                            leg['game_id']
                        ))
                    
                    # Also insert into ev_opportunities for compatibility
                    # We'll insert the first leg as representative
                    first_leg = parlay['legs'][0]
                    cursor.execute("""
                        INSERT INTO ev_opportunities (
                            player_name, ou, market_type, home_team, away_team, line, 
                            ev_percentage, book_count, contest_type, parlay_probability,
                            contest_ev_percent, break_even_probability, edge_over_breakeven
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        f"PARLAY: {parlay['contest_type']} ({len(parlay['legs'])} legs)",
                        'P',  # P for parlay
                        f"{first_leg['player_name']} + {len(parlay['legs'])-1} more",
                        first_leg['home'],
                        first_leg['away'],
                        0,  # No single line for parlay
                        parlay['ev_result']['contest_ev_percent'],  # Use contest EV
                        len(parlay['legs']),  # Leg count instead of book count
                        parlay['contest_type'],
                        parlay['parlay_probability'],
                        parlay['ev_result']['contest_ev_percent'],
                        parlay['ev_result']['break_even_probability'],
                        parlay['ev_result']['edge_over_breakeven']
                    ))
                    
                    inserted_count += 1
                    
                except pymysql.IntegrityError:
                    # Duplicate parlay, skip
                    continue
            
            conn.commit()
            logger.info(f"[Parlay Report] Successfully inserted {inserted_count} parlays")
            
            # Show top parlays with correlation info
            logger.info("[Parlay Report] Top 5 parlay opportunities:")
            
            # Show detailed info for top parlays
            for i, parlay in enumerate(all_parlays[:5], 1):
                logger.info(f"\n  #{i} {parlay['parlay_type'].upper()} {parlay['contest_type']} Parlay:")
                logger.info(f"    EV: {parlay['ev_result']['contest_ev_percent']:.2f}% | Prob: {parlay['parlay_probability']*100:.2f}%")
                logger.info(f"    Correlation: {parlay['correlation_score']:.2f} | Variance: {parlay['variance_multiplier']:.2f}x")
                logger.info(f"    Risk-Adjusted Score: {parlay['risk_adjusted_score']:.2f}")
                logger.info(f"    Legs:")
                for j, leg in enumerate(parlay['legs'], 1):
                    logger.info(f"      {j}. {leg['player_name']} {leg['market']} {leg['ou']} {leg['line']}")
                
    except pymysql.Error as e:
        logger.error(f"[Parlay Report] Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[Parlay Report] Unexpected error: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("[Parlay Report] Database connection closed")

if __name__ == "__main__":
    print("Running Parlay-Based Create Report script...")
    run_parlay_report()
    print("Parlay report script finished.")