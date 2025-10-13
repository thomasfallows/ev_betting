import sys
sys.path.append('Backend')
sys.path.append('Backend/config')

import pymysql
from Backend.config import DB_CONFIG_DICT

conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

print("\n" + "="*90)
print("SPLASH PROPS - ALL NFL PASSING YARDS")
print("="*90)

# Check all passing yards props in Splash
cursor.execute("""
    SELECT player_name, market, line, team_abbr, game_date
    FROM splash_props
    WHERE sport = 'nfl'
    AND market = 'passing_yards'
    ORDER BY player_name
""")
splash_qbs = cursor.fetchall()

print(f"\nTotal Splash QB Passing Yards Props: {len(splash_qbs)}")
print("\nPlayer Name                   | Line   | Team | Game Date")
print("-" * 90)
for qb in splash_qbs:
    game_date = qb['game_date'].strftime('%Y-%m-%d %H:%M') if qb['game_date'] else 'N/A'
    print(f"{qb['player_name']:27} | {qb['line']:6.1f} | {qb['team_abbr']:4} | {game_date}")

print("\n" + "="*90)
print("ALL NFL PROPS BY MARKET")
print("="*90)

cursor.execute("""
    SELECT market, COUNT(*) as count
    FROM splash_props
    WHERE sport = 'nfl'
    GROUP BY market
    ORDER BY count DESC
""")
markets = cursor.fetchall()

print("\nMarket                    | Count")
print("-" * 50)
for m in markets:
    print(f"{m['market']:25} | {m['count']}")

print(f"\nTotal NFL props in Splash: {sum(m['count'] for m in markets)}")

print("\n" + "="*90)
print("CHECK SPLASH SCRAPER FILTER")
print("="*90)

# Show what the scraper config allows
print("\nFrom splash_scraper.py config:")
print("NFL markets filter: ['passing_yards', 'completions', 'receiving_yards', 'receiving_receptions']")
print("\nThis means the scraper ONLY collects these 4 markets for NFL.")
print("Any other markets on Splash website will be ignored.")

conn.close()
