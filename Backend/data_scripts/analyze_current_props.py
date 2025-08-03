"""
Analyze current prop probabilities to understand why no parlays are generated
"""

import pymysql
import sys
import os
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT
from create_report import american_to_prob, calculate_devigged_probability

conn = pymysql.connect(**DB_CONFIG_DICT)
with conn.cursor() as cursor:
    # Get sample of props with devigged probabilities
    cursor.execute("""
        SELECT 
            sp.player_name,
            sp.market,
            sp.line,
            pp.ou,
            GROUP_CONCAT(CONCAT(pp.book, ':', pp.dxodds) SEPARATOR ', ') as all_odds,
            COUNT(DISTINCT pp.book) as book_count
        FROM splash_props sp
        JOIN player_props pp ON (
            sp.normalized_name = pp.normalized_name
            AND sp.line = pp.line
            AND pp.market = (CASE sp.market 
                WHEN 'pitcher_ks' THEN 'pitcher_strikeouts'
                WHEN 'strikeouts' THEN 'pitcher_strikeouts'
                WHEN 'total_bases' THEN 'batter_total_bases'
                WHEN 'hits' THEN 'batter_hits'
                WHEN 'runs' THEN 'batter_runs_scored'
                ELSE sp.market
            END)
        )
        WHERE pp.dxodds IS NOT NULL
        GROUP BY sp.player_name, sp.market, sp.line, pp.ou
        HAVING book_count >= 3
        ORDER BY book_count DESC
        LIMIT 100
    """)
    
    props = cursor.fetchall()
    
    print("Top Props by Book Coverage:")
    print("="*100)
    
    high_prob_props = []
    
    for prop in props:
        # Parse odds
        books_data = []
        for book_odds in prop['all_odds'].split(', '):
            book, odds = book_odds.split(':')
            books_data.append((book, float(odds), prop['ou']))
        
        # Calculate raw probability
        probs = [american_to_prob(odds) for _, odds, _ in books_data]
        avg_prob = sum(probs) / len(probs)
        
        print(f"\n{prop['player_name']} - {prop['market']} {prop['ou']} {prop['line']}")
        print(f"  Books: {prop['book_count']}")
        print(f"  Odds: {prop['all_odds']}")
        print(f"  Avg Implied Prob: {float(avg_prob)*100:.1f}%")
        
        # Check if has both sides for devigging
        cursor.execute("""
            SELECT pp.book, pp.dxodds, pp.ou
            FROM splash_props sp
            JOIN player_props pp ON (
                sp.normalized_name = pp.normalized_name
                AND sp.line = pp.line
                AND pp.market = %s
            )
            WHERE sp.player_name = %s 
            AND sp.market = %s
            AND sp.line = %s
            AND pp.dxodds IS NOT NULL
        """, (
            prop['market'] if 'batter' in prop['market'] or 'pitcher' in prop['market'] else f"batter_{prop['market']}",
            prop['player_name'],
            prop['market'],
            prop['line']
        ))
        
        all_odds = cursor.fetchall()
        
        if all_odds:
            books_data_full = [(row['book'], row['dxodds'], row['ou']) for row in all_odds]
            over_prob, under_prob, has_both = calculate_devigged_probability(books_data_full)
            
            if has_both:
                true_prob = over_prob if prop['ou'] == 'O' else under_prob
                print(f"  DEVIGGED PROB: {float(true_prob)*100:.1f}%")
                
                if true_prob > Decimal('0.57'):
                    high_prob_props.append({
                        'player': prop['player_name'],
                        'market': prop['market'],
                        'ou': prop['ou'],
                        'line': prop['line'],
                        'prob': float(true_prob)
                    })
    
    print("\n\nHIGH PROBABILITY PROPS (>57%):")
    print("="*100)
    for p in sorted(high_prob_props, key=lambda x: x['prob'], reverse=True):
        print(f"{p['player']} - {p['market']} {p['ou']} {p['line']} - {p['prob']*100:.1f}%")
    
    if len(high_prob_props) >= 2:
        print(f"\nBest possible 2-leg parlay:")
        p1, p2 = high_prob_props[0], high_prob_props[1]
        parlay_prob = p1['prob'] * p2['prob']
        print(f"  {p1['player']} ({p1['prob']*100:.1f}%) + {p2['player']} ({p2['prob']*100:.1f}%)")
        print(f"  Parlay probability: {parlay_prob*100:.1f}%")
        print(f"  Need 40% for safety, 33.33% to break even")

conn.close()