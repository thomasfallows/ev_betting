import sys
sys.path.append('Backend')
sys.path.append('Backend/config')

import pymysql
from Backend.config import DB_CONFIG_DICT

conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

print("\n" + "="*90)
print("CHECKING OVER/UNDER AVAILABILITY FOR QB PASSING YARDS")
print("="*90)

# Check what O/U we have for matched QB passing yards props
cursor.execute("""
    SELECT
        sp.player_name,
        sp.line as splash_line,
        pp.line as book_line,
        pp.ou,
        pp.book,
        pp.dxodds
    FROM splash_props sp
    JOIN player_props pp ON (
        sp.normalized_name = pp.normalized_name
        AND ABS(sp.line - pp.line) <= 1.0
        AND pp.market = 'player_pass_yds'
        AND pp.sport = 'nfl'
    )
    WHERE sp.sport = 'nfl'
    AND sp.market = 'passing_yards'
    ORDER BY sp.player_name, pp.line, pp.ou, pp.book
""")
all_odds = cursor.fetchall()

print(f"\nTotal odds records: {len(all_odds)}")
print("\nQB Name                   | Splash | Book   | O/U | Book         | Odds")
print("-" * 90)
for row in all_odds:
    print(f"{row['player_name']:25} | {row['splash_line']:6.1f} | {row['book_line']:6.1f} | {row['ou']:3} | {row['book']:12} | {row['dxodds']}")

# Group by player/line and check if we have both O and U
print("\n" + "="*90)
print("OVER/UNDER PAIR CHECK")
print("="*90)

cursor.execute("""
    SELECT
        sp.player_name,
        sp.line as splash_line,
        pp.line as book_line,
        GROUP_CONCAT(DISTINCT pp.ou) as ou_sides,
        COUNT(DISTINCT CASE WHEN pp.ou = 'O' THEN pp.book END) as over_books,
        COUNT(DISTINCT CASE WHEN pp.ou = 'U' THEN pp.book END) as under_books
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
pairs = cursor.fetchall()

print("\nQB Name                   | Splash | Book   | Sides | O Books | U Books | Status")
print("-" * 95)
for row in pairs:
    splash = row['splash_line']
    book = row['book_line']
    sides = row['ou_sides']
    o_books = row['over_books']
    u_books = row['under_books']

    has_both = 'O' in sides and 'U' in sides
    status = "BOTH" if has_both else "MISSING " + ("U" if 'O' in sides else "O")

    print(f"{row['player_name']:25} | {splash:6.1f} | {book:6.1f} | {sides:5} | {o_books:7} | {u_books:7} | {status}")

print("\n" + "="*90)
print("ISSUE: Props need BOTH Over and Under odds for de-vigging")
print("If any props show 'MISSING O' or 'MISSING U', they won't generate correlations")
print("="*90)

conn.close()
