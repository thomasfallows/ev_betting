import pymysql
import sys
import os
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT

# Run the original create_report to see individual leg EV
from create_report import run_create_report_script

print("Running original create_report.py to see individual leg EVs...")
run_create_report_script()

# Now check what we have
conn = pymysql.connect(**DB_CONFIG_DICT)
with conn.cursor() as cursor:
    # Check top individual EVs
    cursor.execute("""
        SELECT player_name, market_type, ou, line, ev_percentage
        FROM ev_opportunities
        WHERE ev_percentage > 0
        ORDER BY ev_percentage DESC
        LIMIT 10
    """)
    
    print("\nTop 10 positive EV individual legs:")
    for row in cursor.fetchall():
        # Calculate implied probability from EV
        # EV% = (true_prob - 57.74%) * 100
        # So true_prob = (EV% / 100) + 0.5774
        true_prob = (row['ev_percentage'] / 100) + Decimal('0.5774')
        print(f"{row['player_name']} {row['market_type']} {row['ou']} {row['line']} - EV: {row['ev_percentage']:.2f}% - True Prob: {true_prob:.4f}")
    
    print("\n2-leg parlay probabilities if we combine top 2:")
    cursor.execute("""
        SELECT player_name, market_type, ou, line, ev_percentage
        FROM ev_opportunities
        WHERE ev_percentage > 0
        ORDER BY ev_percentage DESC
        LIMIT 2
    """)
    
    legs = cursor.fetchall()
    if len(legs) >= 2:
        prob1 = (legs[0]['ev_percentage'] / 100) + Decimal('0.5774')
        prob2 = (legs[1]['ev_percentage'] / 100) + Decimal('0.5774')
        parlay_prob = prob1 * prob2
        print(f"Leg 1: {legs[0]['player_name']} - Prob: {prob1:.4f}")
        print(f"Leg 2: {legs[1]['player_name']} - Prob: {prob2:.4f}")
        print(f"Parlay probability: {parlay_prob:.4f} ({parlay_prob*100:.2f}%)")
        print(f"Need 40% for safety with $60 bankroll")
        print(f"Break-even is 33.33% for 2-man contests")

conn.close()