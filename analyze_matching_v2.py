import sys
sys.path.append('Backend')
sys.path.append('Backend/config')

import pymysql
from Backend.config import DB_CONFIG_DICT

# Connect to database
conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

print("\n" + "="*80)
print("CHECKING WHAT'S ACTUALLY IN THE TABLES")
print("="*80)

# Check MLB splash props
cursor.execute("SELECT COUNT(*) as count FROM splash_props WHERE sport = 'mlb'")
mlb_splash = cursor.fetchone()['count']
print(f"\nMLB Splash Props: {mlb_splash}")

# Check MLB player_props
cursor.execute("SELECT COUNT(*) as count FROM player_props WHERE sport = 'mlb'")
mlb_books = cursor.fetchone()['count']
print(f"MLB Sportsbook Props: {mlb_books}")

# Check NFL splash props
cursor.execute("SELECT COUNT(*) as count FROM splash_props WHERE sport = 'nfl'")
nfl_splash = cursor.fetchone()['count']
print(f"\nNFL Splash Props: {nfl_splash}")

# Check NFL player_props
cursor.execute("SELECT COUNT(*) as count FROM player_props WHERE sport = 'nfl'")
nfl_books = cursor.fetchone()['count']
print(f"NFL Sportsbook Props: {nfl_books}")

print("\n" + "="*80)
print("MLB SAMPLE DATA")
print("="*80)

# Sample MLB splash props
cursor.execute("""
    SELECT player_name, market, line
    FROM splash_props
    WHERE sport = 'mlb'
    LIMIT 5
""")
print("\nMLB Splash Props (sample):")
for row in cursor.fetchall():
    print(f"  {row['player_name']:25} | {row['market']:20} | {row['line']}")

# Sample MLB player_props
cursor.execute("""
    SELECT Player, market, line
    FROM player_props
    WHERE sport = 'mlb'
    LIMIT 5
""")
print("\nMLB Sportsbook Props (sample):")
for row in cursor.fetchall():
    print(f"  {row['Player']:25} | {row['market']:20} | {row['line']}")

print("\n" + "="*80)
print("NFL SAMPLE DATA")
print("="*80)

# Sample NFL splash props
cursor.execute("""
    SELECT player_name, market, line
    FROM splash_props
    WHERE sport = 'nfl'
    LIMIT 10
""")
print("\nNFL Splash Props (sample):")
for row in cursor.fetchall():
    print(f"  {row['player_name']:25} | {row['market']:20} | {row['line']}")

# Sample NFL player_props
cursor.execute("""
    SELECT Player, market, line, position_football
    FROM player_props
    WHERE sport = 'nfl'
    LIMIT 10
""")
print("\nNFL Sportsbook Props (sample):")
for row in cursor.fetchall():
    pos = row.get('position_football', 'N/A') or 'N/A'
    print(f"  {row['Player']:25} | {row['market']:20} | {row['line']:6} | {pos}")

print("\n" + "="*80)
print("CHECKING FOR ACTUAL MATCHES")
print("="*80)

# Check MLB matches with correct market mapping
cursor.execute("""
    SELECT
        sp.player_name,
        sp.market as splash_market,
        sp.line as splash_line,
        pp.market as book_market,
        pp.line as book_line,
        COUNT(*) as match_count
    FROM splash_props sp
    JOIN player_props pp ON (
        sp.normalized_name = pp.normalized_name
        AND ABS(sp.line - pp.line) < 0.01
        AND pp.sport = 'mlb'
    )
    WHERE sp.sport = 'mlb'
    GROUP BY sp.player_name, sp.market, sp.line, pp.market, pp.line
    LIMIT 10
""")
mlb_matches = cursor.fetchall()
print(f"\nMLB Matches Found (without market mapping): {len(mlb_matches)}")
for row in mlb_matches:
    print(f"  {row['player_name']:20} | Splash: {row['splash_market']:15} | Book: {row['book_market']:20} | Line: {row['splash_line']}")

# Check if markets align
cursor.execute("""
    SELECT DISTINCT sp.market as splash_market, pp.market as book_market
    FROM splash_props sp
    JOIN player_props pp ON sp.normalized_name = pp.normalized_name
    WHERE sp.sport = 'mlb' AND pp.sport = 'mlb'
    LIMIT 20
""")
print("\n\nSplash Market vs Book Market Names:")
for row in cursor.fetchall():
    print(f"  Splash: {row['splash_market']:25} | Book: {row['book_market']:25}")

conn.close()
