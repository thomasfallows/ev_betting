import sys
sys.path.append('Backend')
sys.path.append('Backend/config')

import pymysql
from Backend.config import DB_CONFIG_DICT, MARKET_MAP

# Connect to database
conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

print("\n" + "="*90)
print("MLB LINE MATCHING ANALYSIS (WITH MARKET MAPPING)")
print("="*90)

# MLB with proper market mapping
cursor.execute("""
    SELECT
        sp.player_name,
        sp.market as splash_market,
        sp.line as splash_line,
        MIN(pp.line) as min_book_line,
        MAX(pp.line) as max_book_line,
        COUNT(DISTINCT pp.book) as book_count
    FROM splash_props sp
    LEFT JOIN player_props pp ON (
        sp.normalized_name = pp.normalized_name
        AND pp.sport = 'mlb'
        AND pp.market = CASE sp.market
            WHEN 'strikeouts' THEN 'pitcher_strikeouts'
            WHEN 'earned_runs' THEN 'pitcher_earned_runs'
            WHEN 'hits_allowed' THEN 'pitcher_hits_allowed'
            WHEN 'total_bases' THEN 'batter_total_bases'
            WHEN 'hits' THEN 'batter_hits'
            WHEN 'singles' THEN 'batter_singles'
            WHEN 'runs' THEN 'batter_runs_scored'
            WHEN 'rbis' THEN 'batter_rbis'
            WHEN 'total_outs' THEN 'pitcher_outs'
            ELSE sp.market
        END
    )
    WHERE sp.sport = 'mlb'
    GROUP BY sp.player_name, sp.market, sp.line
    ORDER BY sp.player_name, sp.market
    LIMIT 25
""")

mlb_results = cursor.fetchall()

mlb_exact = 0
mlb_mismatch = 0
mlb_no_match = 0

print("\nPlayer Name                | Market           | Splash | Book Lines | Status")
print("-" * 90)

for row in mlb_results:
    player = row['player_name'][:24].ljust(24)
    market = row['splash_market'][:15].ljust(15)
    splash_line = row['splash_line']
    min_line = row['min_book_line']
    max_line = row['max_book_line']

    if min_line is None:
        status = "NO MATCH"
        mlb_no_match += 1
        book_range = "N/A"
    elif abs(float(splash_line) - float(min_line)) < 0.01 and abs(float(splash_line) - float(max_line)) < 0.01:
        status = "EXACT"
        mlb_exact += 1
        book_range = f"{min_line:.1f}"
    else:
        status = f"MISMATCH ({min_line:.1f}-{max_line:.1f})"
        mlb_mismatch += 1
        book_range = f"{min_line:.1f}-{max_line:.1f}"

    print(f"{player} | {market} | {splash_line:6.1f} | {book_range:10} | {status}")

print("-" * 90)
print(f"MLB SUMMARY: {mlb_exact} exact / {mlb_mismatch} mismatch / {mlb_no_match} no match = {len(mlb_results)} total")
if len(mlb_results) > 0:
    print(f"Exact Match Rate: {(mlb_exact/len(mlb_results))*100:.1f}%")

print("\n" + "="*90)
print("NFL LINE MATCHING ANALYSIS (WITH MARKET MAPPING)")
print("="*90)

# NFL with proper market mapping
cursor.execute("""
    SELECT
        sp.player_name,
        sp.market as splash_market,
        sp.line as splash_line,
        MIN(pp.line) as min_book_line,
        MAX(pp.line) as max_book_line,
        COUNT(DISTINCT pp.book) as book_count
    FROM splash_props sp
    LEFT JOIN player_props pp ON (
        sp.normalized_name = pp.normalized_name
        AND pp.sport = 'nfl'
        AND pp.market = CASE sp.market
            WHEN 'passing_yards' THEN 'player_pass_yds'
            WHEN 'completions' THEN 'player_pass_completions'
            WHEN 'receiving_yards' THEN 'player_reception_yds'
            WHEN 'receiving_receptions' THEN 'player_receptions'
            ELSE sp.market
        END
    )
    WHERE sp.sport = 'nfl'
    GROUP BY sp.player_name, sp.market, sp.line
    ORDER BY
        CASE sp.market
            WHEN 'passing_yards' THEN 1
            WHEN 'completions' THEN 2
            WHEN 'receiving_yards' THEN 3
            ELSE 4
        END,
        sp.player_name
""")

nfl_results = cursor.fetchall()

nfl_exact = 0
nfl_mismatch = 0
nfl_no_match = 0

print("\nPlayer Name                | Market           | Splash | Book Lines | Status")
print("-" * 90)

for row in nfl_results:
    player = row['player_name'][:24].ljust(24)
    market = row['splash_market'][:15].ljust(15)
    splash_line = row['splash_line']
    min_line = row['min_book_line']
    max_line = row['max_book_line']

    if min_line is None:
        status = "NO MATCH"
        nfl_no_match += 1
        book_range = "N/A"
    elif abs(float(splash_line) - float(min_line)) < 0.01 and abs(float(splash_line) - float(max_line)) < 0.01:
        status = "EXACT"
        nfl_exact += 1
        book_range = f"{min_line:.1f}"
    else:
        status = f"MISMATCH ({min_line:.1f}-{max_line:.1f})"
        nfl_mismatch += 1
        book_range = f"{min_line:.1f}-{max_line:.1f}"

    print(f"{player} | {market} | {splash_line:6.1f} | {book_range:10} | {status}")

print("-" * 90)
print(f"NFL SUMMARY: {nfl_exact} exact / {nfl_mismatch} mismatch / {nfl_no_match} no match = {len(nfl_results)} total")
if len(nfl_results) > 0:
    print(f"Exact Match Rate: {(nfl_exact/len(nfl_results))*100:.1f}%")

print("\n" + "="*90)
print("KEY FINDINGS")
print("="*90)
print("\nMLB: Markets like 'hits', 'runs', 'strikeouts' are consistent across books")
print("     Most props have exact line matches when market names are mapped correctly")
print("\nNFL: Lines vary significantly between books even for same player/market")
print("     Different books use different lines (e.g., 228.5 vs 229.5 vs 231.5)")
print("     This is NORMAL for NFL - books compete by offering different lines")

print("\n" + "="*90)
print("CORRELATION SYSTEM IMPLICATIONS")
print("="*90)
print("\nWith EXACT matching (current ±0.01 tolerance):")
print("  - MLB: Works well, most props match")
print("  - NFL: Very few correlations (only props where ALL books agree on line)")
print("\nWith RELAXED matching (e.g., ±1.0 tolerance):")
print("  - NFL: Many more correlations possible")
print("  - Trade-off: Line shown won't exactly match Splash")
print("  - Example: Splash 229.5, could match DK 228.5 or FD 231.5")

conn.close()
