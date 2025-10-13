import sys
sys.path.append('Backend')
sys.path.append('Backend/config')

import pymysql
from Backend.config import DB_CONFIG_DICT

# Connect to database
conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

print("\n" + "="*80)
print("MLB LINE MATCHING ANALYSIS")
print("="*80)

# Get MLB Splash props with their corresponding sportsbook lines
query = """
SELECT
    sp.player_name,
    sp.market,
    sp.line as splash_line,
    MIN(pp.line) as min_book_line,
    MAX(pp.line) as max_book_line,
    COUNT(DISTINCT pp.book) as book_count
FROM splash_props sp
LEFT JOIN player_props pp ON (
    sp.normalized_name = pp.normalized_name
    AND sp.market = pp.market
    AND pp.sport = 'mlb'
)
WHERE sp.sport = 'mlb'
GROUP BY sp.player_name, sp.market, sp.line
ORDER BY sp.player_name, sp.market
LIMIT 20
"""

cursor.execute(query)
results = cursor.fetchall()

exact_matches = 0
no_matches = 0
line_mismatches = 0

print("\nPlayer Name                    | Market              | Splash | Books      | Status")
print("-" * 95)

for row in results:
    player = row['player_name'][:28].ljust(28)
    market = row['market'][:18].ljust(18)
    splash_line = row['splash_line']
    min_line = row['min_book_line']
    max_line = row['max_book_line']
    book_count = row['book_count']

    if min_line is None or max_line is None:
        status = "NO MATCH FOUND"
        no_matches += 1
    elif abs(float(splash_line) - float(min_line)) < 0.01 and abs(float(splash_line) - float(max_line)) < 0.01:
        status = "EXACT MATCH"
        exact_matches += 1
    else:
        status = f"MISMATCH (diff: {min_line - splash_line:.1f} to {max_line - splash_line:.1f})"
        line_mismatches += 1

    book_range = f"{min_line}-{max_line}" if min_line else "N/A"
    print(f"{player} | {market} | {splash_line:6.1f} | {book_range:10} | {status}")

print("-" * 95)
print(f"\nSUMMARY:")
print(f"  Exact Matches:     {exact_matches}")
print(f"  Line Mismatches:   {line_mismatches}")
print(f"  No Matches Found:  {no_matches}")
print(f"  Total Props:       {len(results)}")

if len(results) > 0:
    match_rate = (exact_matches / len(results)) * 100
    print(f"\n  Exact Match Rate:  {match_rate:.1f}%")

print("\n" + "="*80)
print("NFL LINE MATCHING ANALYSIS (PASSING YARDS - KEY MARKET)")
print("="*80)

# Check NFL QB passing yards specifically
query = """
SELECT
    sp.player_name,
    sp.market,
    sp.line as splash_line,
    MIN(pp.line) as min_book_line,
    MAX(pp.line) as max_book_line,
    COUNT(DISTINCT pp.book) as book_count
FROM splash_props sp
LEFT JOIN player_props pp ON (
    sp.normalized_name = pp.normalized_name
    AND pp.market = 'player_pass_yds'
    AND pp.sport = 'nfl'
)
WHERE sp.sport = 'nfl'
AND sp.market = 'passing_yards'
GROUP BY sp.player_name, sp.market, sp.line
ORDER BY sp.player_name
"""

cursor.execute(query)
nfl_results = cursor.fetchall()

nfl_exact = 0
nfl_no_match = 0
nfl_mismatch = 0

print("\nQB Name                        | Market              | Splash | Books      | Status")
print("-" * 95)

for row in nfl_results:
    player = row['player_name'][:28].ljust(28)
    market = "player_pass_yds".ljust(18)
    splash_line = row['splash_line']
    min_line = row['min_book_line']
    max_line = row['max_book_line']

    if min_line is None or max_line is None:
        status = "NO MATCH FOUND"
        nfl_no_match += 1
    elif abs(float(splash_line) - float(min_line)) < 0.01 and abs(float(splash_line) - float(max_line)) < 0.01:
        status = "EXACT MATCH"
        nfl_exact += 1
    else:
        status = f"MISMATCH (diff: {min_line - splash_line:.1f} to {max_line - splash_line:.1f})"
        nfl_mismatch += 1

    book_range = f"{min_line}-{max_line}" if min_line else "N/A"
    print(f"{player} | {market} | {splash_line:6.1f} | {book_range:10} | {status}")

print("-" * 95)
print(f"\nNFL SUMMARY:")
print(f"  Exact Matches:     {nfl_exact}")
print(f"  Line Mismatches:   {nfl_mismatch}")
print(f"  No Matches Found:  {nfl_no_match}")
print(f"  Total QBs:         {len(nfl_results)}")

if len(nfl_results) > 0:
    match_rate = (nfl_exact / len(nfl_results)) * 100
    print(f"\n  Exact Match Rate:  {match_rate:.1f}%")

conn.close()

print("\n" + "="*80)
print("CONCLUSION:")
print("="*80)
print("\nMLB: Most props match exactly because lines are typically whole/half numbers")
print("     that books agree on (e.g., 5.5 strikeouts)")
print("\nNFL: Most props DON'T match exactly because books use different lines")
print("     (e.g., Splash: 229.5 yards, DK: 228.5, FD: 231.5)")
print("\nThis is why MLB correlations work well but NFL has very few matches.")
print("="*80)
