import sys
sys.path.append('Backend')
sys.path.append('Backend/config')

import pymysql
from Backend.config import DB_CONFIG_DICT

conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

print("\n" + "="*100)
print("DEBUGGING: WHY QBs AREN'T SHOWING IN CORRELATIONS")
print("="*100)

# Get all 5 QBs from Splash
cursor.execute("""
    SELECT player_name, line, team_abbr
    FROM splash_props
    WHERE sport = 'nfl'
    AND market = 'passing_yards'
    ORDER BY player_name
""")
splash_qbs = cursor.fetchall()

for qb in splash_qbs:
    qb_name = qb['player_name']
    splash_line = qb['line']
    team = qb['team_abbr']

    print(f"\n{'='*100}")
    print(f"QB: {qb_name} ({team}) - Splash Line: {splash_line}")
    print('='*100)

    # Check if sportsbook has this QB within ±1.6
    cursor.execute("""
        SELECT pp.line, pp.ou, pp.book, pp.dxodds, pp.home, pp.away
        FROM player_props pp
        WHERE pp.normalized_name = %s
        AND pp.sport = 'nfl'
        AND pp.market = 'player_pass_yds'
        AND ABS(pp.line - %s) <= 1.6
        ORDER BY pp.line, pp.ou, pp.book
    """, (qb_name, splash_line))
    book_odds = cursor.fetchall()

    if not book_odds:
        print(f"[X] NO SPORTSBOOK MATCH within +/-1.6 of {splash_line}")

        # Show what lines books DO have
        cursor.execute("""
            SELECT DISTINCT line
            FROM player_props
            WHERE normalized_name = %s
            AND sport = 'nfl'
            AND market = 'player_pass_yds'
            ORDER BY line
        """, (qb_name,))
        actual_lines = cursor.fetchall()
        if actual_lines:
            lines_str = ", ".join([str(l['line']) for l in actual_lines])
            print(f"   Books have lines: {lines_str}")
        else:
            print(f"   Books have NO lines for this QB")
        continue

    print(f"[OK] Found {len(book_odds)} sportsbook odds within +/-1.6")

    # Check for O/U pairs
    game = book_odds[0]['home'] + ' vs ' + book_odds[0]['away']
    lines = {}
    for odd in book_odds:
        line_key = odd['line']
        if line_key not in lines:
            lines[line_key] = {'O': [], 'U': []}
        lines[line_key][odd['ou']].append(odd['book'])

    print(f"   Game: {game}")
    print(f"   Lines found:")
    for line, sides in lines.items():
        has_both = len(sides['O']) > 0 and len(sides['U']) > 0
        status = "[OK] BOTH" if has_both else "[X] MISSING " + ("U" if len(sides['O']) > 0 else "O")
        print(f"      {line}: O books={len(sides['O'])}, U books={len(sides['U'])} - {status}")

    # Check if there are matching receivers
    cursor.execute("""
        SELECT COUNT(*) as receiver_count
        FROM splash_props sp
        JOIN player_props pp ON (
            sp.normalized_name = pp.normalized_name
            AND ABS(sp.line - pp.line) <= 1.6
            AND pp.market = 'player_reception_yds'
            AND pp.sport = 'nfl'
        )
        WHERE sp.sport = 'nfl'
        AND sp.market = 'receiving_yards'
        AND (pp.home = %s OR pp.away = %s)
    """, (game.split(' vs ')[0], game.split(' vs ')[1]))
    receiver_result = cursor.fetchone()
    receiver_count = receiver_result['receiver_count'] if receiver_result else 0

    print(f"   Matching receivers in this game: {receiver_count}")

    if receiver_count == 0:
        print(f"   [X] NO RECEIVERS - Cannot build correlation stack")

conn.close()
