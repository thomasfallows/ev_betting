import sys
sys.path.append('Backend')
sys.path.append('Backend/config')

import pymysql
from Backend.config import DB_CONFIG_DICT

conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

print("\n" + "="*90)
print("CHECKING QB PASSING YARDS MATCHING WITH ±1.0 TOLERANCE")
print("="*90)

# Check Splash QB passing yards props
cursor.execute("""
    SELECT player_name, line
    FROM splash_props
    WHERE sport = 'nfl'
    AND market = 'passing_yards'
    ORDER BY player_name
""")
splash_qbs = cursor.fetchall()

print(f"\nSplash QB Passing Yards Props: {len(splash_qbs)}")
for qb in splash_qbs:
    print(f"  {qb['player_name']:25} | {qb['line']}")

# Check sportsbook QB passing yards props
cursor.execute("""
    SELECT DISTINCT Player, line
    FROM player_props
    WHERE sport = 'nfl'
    AND market = 'player_pass_yds'
    ORDER BY Player
""")
book_qbs = cursor.fetchall()

print(f"\nSportsbook QB Passing Yards Props: {len(book_qbs)}")
for qb in book_qbs:
    print(f"  {qb['Player']:25} | {qb['line']}")

# Now check matches with ±1.0 tolerance
print("\n" + "="*90)
print("MATCHING ANALYSIS (±1.0 TOLERANCE)")
print("="*90)

cursor.execute("""
    SELECT
        sp.player_name,
        sp.line as splash_line,
        pp.line as book_line,
        ABS(sp.line - pp.line) as diff,
        COUNT(DISTINCT pp.book) as book_count
    FROM splash_props sp
    JOIN player_props pp ON (
        sp.normalized_name = pp.normalized_name
        AND ABS(sp.line - pp.line) <= 1.0
        AND pp.market = 'player_pass_yds'
        AND pp.sport = 'nfl'
    )
    WHERE sp.sport = 'nfl'
    AND sp.market = 'passing_yards'
    GROUP BY sp.player_name, sp.line, pp.line
    ORDER BY sp.player_name, pp.line
""")
matches = cursor.fetchall()

print(f"\nMatches found: {len(matches)}")
print("\nQB Name                   | Splash | Books  | Diff | Book Count")
print("-" * 90)
for match in matches:
    print(f"{match['player_name']:25} | {match['splash_line']:6.1f} | {match['book_line']:6.1f} | {match['diff']:4.1f} | {match['book_count']}")

# Check if normalized names match
print("\n" + "="*90)
print("NORMALIZED NAME CHECK")
print("="*90)

cursor.execute("""
    SELECT DISTINCT
        sp.player_name as splash_name,
        sp.normalized_name as splash_norm,
        pp.Player as book_name,
        pp.normalized_name as book_norm
    FROM splash_props sp
    JOIN player_props pp ON sp.normalized_name = pp.normalized_name
    WHERE sp.sport = 'nfl'
    AND sp.market = 'passing_yards'
    AND pp.sport = 'nfl'
    AND pp.market = 'player_pass_yds'
""")
norm_matches = cursor.fetchall()

print(f"\nNormalized name matches: {len(norm_matches)}")
for match in norm_matches:
    if match['splash_norm'] == match['book_norm']:
        print(f"OK: {match['splash_name']:20} == {match['book_name']:20} | norm: {match['splash_norm']}")
    else:
        print(f"FAIL: {match['splash_name']:20} != {match['book_name']:20}")

conn.close()
