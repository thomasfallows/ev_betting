import pymysql
from config import DB_CONFIG_DICT
from decimal import Decimal

conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

# Check pitcher EV opportunities
print("=== PITCHER EV OPPORTUNITIES ===")
cursor.execute("""
    SELECT player_name, market_type, line, ou, ev_percentage
    FROM ev_opportunities
    WHERE market_type LIKE '%pitcher%' OR market_type IN ('strikeouts', 'earned_runs', 'allowed_hits', 'hits_allowed', 'outs', 'total_outs')
    ORDER BY ev_percentage DESC
    LIMIT 20
""")
for row in cursor.fetchall():
    print(f"{row['player_name']}: {row['market_type']} {row['ou']} {row['line']} -> {row['ev_percentage']}% EV")

print("\n=== ALL POSITIVE EV PROPS ===")
cursor.execute("""
    SELECT player_name, market_type, line, ou, ev_percentage
    FROM ev_opportunities
    WHERE ev_percentage > 0
    ORDER BY ev_percentage DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(f"{row['player_name']}: {row['market_type']} {row['ou']} {row['line']} -> {row['ev_percentage']}% EV")

cursor.close()
conn.close()