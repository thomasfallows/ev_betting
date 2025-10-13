import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

conn = pymysql.connect(
    host='localhost',
    user='root',
    password=os.getenv('DB_PASSWORD'),
    database='MyDatabase',
    cursorclass=pymysql.cursors.DictCursor
)

cursor = conn.cursor()

print("=" * 60)
print("CHECKING PARLAY DATA")
print("=" * 60)

# Check pitchers with earned_runs
print("\nPITCHERS WITH EARNED RUNS:")
cursor.execute("""
    SELECT player_name, market, line, over_under, ev_percentage, home_team, away_team
    FROM ev_opportunities
    WHERE league = 'mlb' AND market = 'earned_runs'
    ORDER BY ev_percentage DESC
    LIMIT 5
""")
pitchers = cursor.fetchall()
for p in pitchers:
    print(f"  {p['player_name']}: {p['market']} {p['over_under']} {p['line']} (EV: {p['ev_percentage']}%)")
    print(f"    Game: {p['away_team']} @ {p['home_team']}")

# Check batters with runs
print("\nBATTERS WITH RUNS:")
cursor.execute("""
    SELECT player_name, market, line, over_under, ev_percentage, home_team, away_team
    FROM ev_opportunities
    WHERE league = 'mlb' AND market = 'runs'
    ORDER BY ev_percentage DESC
    LIMIT 5
""")
batters = cursor.fetchall()
for b in batters:
    print(f"  {b['player_name']}: {b['market']} {b['over_under']} {b['line']} (EV: {b['ev_percentage']}%)")
    print(f"    Game: {b['away_team']} @ {b['home_team']}")

# Check for matching games
print("\n" + "=" * 60)
print("CHECKING FOR CORRELATIONS:")

cursor.execute("""
    SELECT DISTINCT
        p.player_name as pitcher,
        p.ev_percentage as pitcher_ev,
        p.home_team,
        p.away_team
    FROM ev_opportunities p
    WHERE p.league = 'mlb' AND p.market = 'earned_runs'
""")

pitchers = cursor.fetchall()
correlations_found = 0

for pitcher in pitchers:
    # Find batters in the same game
    cursor.execute("""
        SELECT player_name, market, line, over_under, ev_percentage
        FROM ev_opportunities
        WHERE league = 'mlb'
        AND market = 'runs'
        AND home_team = %s
        AND away_team = %s
        AND player_name != %s
    """, (pitcher['home_team'], pitcher['away_team'], pitcher['pitcher']))

    batters = cursor.fetchall()
    if batters:
        correlations_found += 1
        print(f"\nFound correlation for {pitcher['pitcher']} (EV: {pitcher['pitcher_ev']}%):")
        for batter in batters:
            print(f"  - {batter['player_name']}: {batter['market']} {batter['over_under']} {batter['line']} (EV: {batter['ev_percentage']}%)")

if correlations_found == 0:
    print("\nNo correlations found - checking why...")

    # Debug: Check unique games
    cursor.execute("""
        SELECT DISTINCT home_team, away_team
        FROM ev_opportunities
        WHERE league = 'mlb' AND market = 'earned_runs'
    """)
    pitcher_games = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT home_team, away_team
        FROM ev_opportunities
        WHERE league = 'mlb' AND market = 'runs'
    """)
    batter_games = cursor.fetchall()

    print(f"\nPitcher games: {len(pitcher_games)}")
    print(f"Batter games: {len(batter_games)}")

    # Check for overlapping games
    pitcher_game_set = {(g['home_team'], g['away_team']) for g in pitcher_games}
    batter_game_set = {(g['home_team'], g['away_team']) for g in batter_games}

    overlapping = pitcher_game_set & batter_game_set
    print(f"Overlapping games: {len(overlapping)}")

    if overlapping:
        print("\nSample overlapping game:")
        sample = list(overlapping)[0]
        print(f"  {sample[1]} @ {sample[0]}")

conn.close()