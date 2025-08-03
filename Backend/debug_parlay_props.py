import pymysql
from config import DB_CONFIG_DICT
from data_scripts.create_report_parlay import calculate_devigged_probability
from decimal import Decimal

conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

# Check what props we get from the join
print("=== PROPS FROM JOIN ===")
cursor.execute("""
    SELECT 
        sp.player_name,
        sp.market as splash_market,
        sp.line,
        pp.market as pp_market,
        pp.ou,
        pp.dxodds,
        pp.book
    FROM splash_props sp
    JOIN player_props pp ON (
        sp.normalized_name = pp.normalized_name
        AND sp.line = pp.line
        AND pp.market = (CASE sp.market 
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
    AND (sp.market LIKE '%pitcher%' OR sp.market IN ('strikeouts', 'earned_runs', 'allowed_hits', 'hits_allowed', 'outs', 'total_outs'))
    ORDER BY sp.player_name, sp.market
    LIMIT 20
""")

results = cursor.fetchall()
print(f"Found {len(results)} pitcher prop matches")
for row in results:
    print(f"  {row['player_name']}: {row['splash_market']} -> {row['pp_market']} {row['ou']} {row['line']} @ {row['dxodds']} ({row['book']})")

# Group by prop and check devigging
print("\n=== CHECKING DE-VIGGING ===")
cursor.execute("""
    SELECT 
        sp.player_name,
        sp.market,
        sp.line,
        pp.book,
        pp.ou,
        pp.dxodds
    FROM splash_props sp
    JOIN player_props pp ON (
        sp.normalized_name = pp.normalized_name
        AND sp.line = pp.line
        AND pp.market = 'pitcher_strikeouts'
    )
    WHERE sp.market = 'strikeouts'
    AND pp.dxodds IS NOT NULL
    ORDER BY sp.player_name, pp.book, pp.ou
""")

# Group by player/line
props_by_player = {}
for row in cursor.fetchall():
    key = (row['player_name'], row['line'])
    if key not in props_by_player:
        props_by_player[key] = []
    props_by_player[key].append((row['book'], row['dxodds'], row['ou']))

for (player, line), books_data in props_by_player.items():
    print(f"\n{player} - Strikeouts {line}")
    # Group by book
    by_book = {}
    for book, odds, ou in books_data:
        if book not in by_book:
            by_book[book] = {}
        by_book[book][ou] = odds
    
    # Show which books have both sides
    for book, sides in by_book.items():
        if 'O' in sides and 'U' in sides:
            print(f"  {book}: O {sides['O']} / U {sides['U']} (both sides)")
        else:
            print(f"  {book}: {sides} (one-sided)")

cursor.close()
conn.close()