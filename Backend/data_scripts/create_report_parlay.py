import pymysql
from decimal import Decimal
import sys
import os
import logging
from datetime import datetime
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config'))
from data_scripts.pitcher_anchored_parlays import PitcherAnchoredParlayGenerator

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

def generate_parlay_hash(legs):
    """Generate unique hash for a parlay based on its legs"""
    # Sort legs to ensure consistent hashing
    sorted_legs = sorted(legs, key=lambda x: f"{x['player_name']}_{x['market']}_{x['line']}_{x['ou']}")
    leg_string = "_".join([f"{leg['player_name']}_{leg['market']}_{leg['line']}_{leg['ou']}" for leg in sorted_legs])
    return hashlib.sha256(leg_string.encode()).hexdigest()

def run_parlay_report():
    """Generate correlation-based parlay report using pitcher anchors"""
    logger.info("[Parlay Report] Starting pitcher-anchored parlay generation...")
    
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

            # Get all props with BOTH sides from the same book (for de-vigging)
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
                sp.team_abbr as team,
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
                        'team': match.get('team'),
                        'books_data': []
                    }
                props_grouped[key]['books_data'].append((match['book'], match['dxodds'], match['ou']))
            
            logger.info(f"[Parlay Report] Found {len(props_grouped)} unique props to analyze")
            
            # Process each prop and collect all props (including negative EV)
            all_props = []
            one_sided_count = 0
            
            for (player_name, normalized_name, market, line), prop_data in props_grouped.items():
                # Calculate de-vigged probability
                over_prob, under_prob, has_both_sides = calculate_devigged_probability(prop_data['books_data'])
                
                if not has_both_sides:
                    one_sided_count += 1
                    continue
                
                # Calculate EV for both sides
                for side, true_prob in [('O', over_prob), ('U', under_prob)]:
                    ev_percentage = (true_prob - SPLASH_IMPLIED_PROB) * 100
                    
                    # Add ALL props (even negative EV)
                    all_props.append({
                        'player_name': player_name,
                        'normalized_name': normalized_name,
                        'market': market,
                        'line': line,
                        'ou': side,
                        'true_probability': float(true_prob),
                        'ev_percentage': float(ev_percentage),
                        'home': prop_data['home'],
                        'away': prop_data['away'],
                        'sport': prop_data['sport'],
                        'team': prop_data['team']
                    })
            
            logger.info(f"[Parlay Report] Skipped {one_sided_count} one-sided props")
            logger.info(f"[Parlay Report] Found {len(all_props)} valid prop sides for parlay generation")
            
            # Generate pitcher-anchored parlays
            generator = PitcherAnchoredParlayGenerator(all_props)
            
            # Get display data for all anchors
            anchor_sections = generator.generate_anchor_display_data(limit=20)  # Top 20 anchors
            
            logger.info(f"[Parlay Report] Found {len(anchor_sections)} pitcher anchors")
            
            # Store some example parlays in database
            stored_count = 0
            for anchor_section in anchor_sections[:5]:  # Store top 5 anchors' parlays
                anchor = anchor_section['anchor']
                
                for correlation_section in anchor_section['correlation_sections'][:2]:  # Top 2 correlations per anchor
                    if correlation_section['batters']:
                        # Create a sample 2-leg parlay with top batter
                        top_batter = correlation_section['batters'][0]
                        
                        # Create parlay legs
                        legs = [
                            {
                                'player_name': anchor['player_name'],
                                'market': anchor['market'],
                                'line': anchor['line'],
                                'ou': anchor['ou'],
                                'ev': anchor['ev']
                            },
                            {
                                'player_name': top_batter['player_name'],
                                'market': correlation_section['market'],
                                'line': top_batter['line'],
                                'ou': correlation_section['direction'],
                                'ev': top_batter['ev']
                            }
                        ]
                        
                        # Calculate combined probability (simplified)
                        combined_prob = 0.25  # Placeholder - would calculate from true probabilities
                        
                        # Generate hash
                        parlay_hash = generate_parlay_hash(legs)
                        
                        # Insert into parlays table
                        cursor.execute("""
                            INSERT INTO parlays (
                                contest_type, parlay_hash, leg_count, parlay_probability,
                                contest_ev_percent, break_even_probability, edge_over_breakeven, meets_minimum
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            '2-man',
                            parlay_hash,
                            2,
                            combined_prob,
                            (combined_prob - 0.3333) * 100,  # Contest EV
                            0.3333,  # Break-even for 2-man
                            combined_prob - 0.3333,
                            1 if combined_prob > 0.3333 else 0
                        ))
                        
                        # Insert legs
                        for i, leg in enumerate(legs):
                            cursor.execute("""
                                INSERT INTO parlay_legs (
                                    parlay_hash, leg_number, player_name, normalized_name,
                                    market, line, ou, true_probability, sport, game_id
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                parlay_hash,
                                i + 1,
                                leg['player_name'],
                                leg['player_name'].lower().replace(' ', '_'),
                                leg['market'],
                                leg['line'],
                                leg['ou'],
                                0.5,  # Placeholder
                                'mlb',
                                None
                            ))
                        
                        stored_count += 1
            
            conn.commit()
            logger.info(f"[Parlay Report] Stored {stored_count} example parlays in database")
            
            # Log summary of top opportunities
            logger.info("\n[Parlay Report] Top Pitcher Anchors:")
            for i, anchor_section in enumerate(anchor_sections[:5], 1):
                anchor = anchor_section['anchor']
                logger.info(f"\n#{i} {anchor['player_name']} - {anchor['market']} {anchor['ou']} {anchor['line']} ({anchor['ev']:+.1f}% EV)")
                
                # Show top correlation
                if anchor_section['correlation_sections']:
                    top_corr = anchor_section['correlation_sections'][0]
                    logger.info(f"   Best correlation: {top_corr['description']}")
                    if top_corr['batters']:
                        logger.info(f"   Top batter: {top_corr['batters'][0]['player_name']} ({top_corr['batters'][0]['ev']:+.1f}% EV)")
                        
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
    print("Running Pitcher-Anchored Parlay Report...")
    run_parlay_report()
    print("Parlay report script finished.")