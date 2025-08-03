import pymysql
from config import DB_CONFIG_DICT

conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

# Check pitcher props in splash_props
print("=== PITCHER PROPS IN SPLASH_PROPS ===")
cursor.execute("""
    SELECT player_name, market, line, team_abbr, sport
    FROM splash_props
    WHERE market LIKE '%pitcher%' OR market IN ('strikeouts', 'earned_runs', 'allowed_hits', 'hits_allowed', 'outs', 'total_outs')
    LIMIT 10
""")
for row in cursor.fetchall():
    print(row)

# Check pitcher props in player_props
print("\n=== PITCHER PROPS IN PLAYER_PROPS ===")
cursor.execute("""
    SELECT Player, market, line, ou, dxodds, book
    FROM player_props
    WHERE market LIKE '%pitcher%'
    LIMIT 10
""")
for row in cursor.fetchall():
    print(row)

# Check EV opportunities
print("\n=== EV OPPORTUNITIES ===")
cursor.execute("""
    SELECT player_name, market_type, line, side, ev_percentage
    FROM ev_opportunities
    WHERE market_type LIKE '%pitcher%' OR market_type IN ('strikeouts', 'earned_runs', 'allowed_hits', 'hits_allowed', 'outs', 'total_outs')
    ORDER BY ev_percentage DESC
    LIMIT 10
""")
for row in cursor.fetchall():
    print(row)

cursor.close()
conn.close()