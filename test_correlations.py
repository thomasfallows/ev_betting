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

print("=" * 80)
print("TESTING PARLAY CORRELATIONS")
print("=" * 80)

# Test 1: Earned Runs + Batter Runs
print("\n1. EARNED RUNS + BATTER RUNS CORRELATION")
print("-" * 80)

pitcher_query = """
    SELECT DISTINCT
        pp.Player as pitcher_name,
        pp.market as pitcher_market,
        pp.line as pitcher_line,
        pp.ou as pitcher_ou,
        pp.home,
        pp.away,
        sp.team_abbr as pitcher_team
    FROM player_props pp
    JOIN splash_props sp ON (
        pp.normalized_name = sp.normalized_name
        AND pp.line = sp.line
        AND pp.market = CASE sp.market
            WHEN 'pitcher_ks' THEN 'pitcher_strikeouts'
            WHEN 'strikeouts' THEN 'pitcher_strikeouts'
            WHEN 'earned_runs' THEN 'pitcher_earned_runs'
            WHEN 'allowed_hits' THEN 'pitcher_hits_allowed'
            WHEN 'hits_allowed' THEN 'pitcher_hits_allowed'
            WHEN 'outs' THEN 'pitcher_outs'
            WHEN 'total_outs' THEN 'pitcher_outs'
            ELSE sp.market
        END
    )
    WHERE pp.market = %s
    AND pp.league = 'MLB'
    GROUP BY pp.Player, pp.market, pp.line, pp.ou, pp.home, pp.away, sp.team_abbr
"""

cursor.execute(pitcher_query, ('pitcher_earned_runs',))
pitchers = cursor.fetchall()
print(f"Found {len(pitchers)} pitchers with earned_runs\n")

for pitcher in pitchers[:3]:  # Test first 3
    print(f"Pitcher: {pitcher['pitcher_name']} ({pitcher['pitcher_team']}) - {pitcher['pitcher_ou']} {pitcher['pitcher_line']}")
    print(f"  Game: {pitcher['away']} @ {pitcher['home']}")

    # Find opposing batters
    batter_query = """
        SELECT DISTINCT
            pp.Player as batter_name,
            pp.market as batter_market,
            pp.line as batter_line,
            pp.ou as batter_ou,
            sp.team_abbr as batter_team
        FROM player_props pp
        JOIN splash_props sp ON (
            pp.normalized_name = sp.normalized_name
            AND pp.line = sp.line
            AND pp.market = CASE sp.market
                WHEN 'hits' THEN 'batter_hits'
                WHEN 'singles' THEN 'batter_singles'
                WHEN 'runs' THEN 'batter_runs_scored'
                WHEN 'rbis' THEN 'batter_rbis'
                WHEN 'total_bases' THEN 'batter_total_bases'
                ELSE sp.market
            END
        )
        WHERE pp.market = %s
        AND pp.league = 'MLB'
        AND pp.home = %s
        AND pp.away = %s
        AND pp.ou = %s
        AND pp.Player != %s
        AND sp.team_abbr != %s
        GROUP BY pp.Player, pp.market, pp.line, pp.ou, sp.team_abbr
        LIMIT 3
    """

    cursor.execute(batter_query, (
        'batter_runs_scored',
        pitcher['home'],
        pitcher['away'],
        pitcher['pitcher_ou'],
        pitcher['pitcher_name'],
        pitcher['pitcher_team']
    ))
    batters = cursor.fetchall()

    print(f"  > Found {len(batters)} opposing batters with matching O/U")
    for batter in batters:
        print(f"     - {batter['batter_name']} ({batter['batter_team']}) - {batter['batter_ou']} {batter['batter_line']}")
    print()

# Test 2: Hits correlation
print("\n2. HITS ALLOWED + BATTER HITS CORRELATION")
print("-" * 80)

cursor.execute(pitcher_query, ('pitcher_hits_allowed',))
pitchers = cursor.fetchall()
print(f"Found {len(pitchers)} pitchers with hits_allowed\n")

for pitcher in pitchers[:2]:  # Test first 2
    print(f"Pitcher: {pitcher['pitcher_name']} ({pitcher['pitcher_team']}) - {pitcher['pitcher_ou']} {pitcher['pitcher_line']}")

    batter_query = """
        SELECT COUNT(*) as cnt
        FROM player_props pp
        JOIN splash_props sp ON (
            pp.normalized_name = sp.normalized_name
            AND pp.line = sp.line
            AND pp.market = CASE sp.market
                WHEN 'hits' THEN 'batter_hits'
                WHEN 'singles' THEN 'batter_singles'
                WHEN 'runs' THEN 'batter_runs_scored'
                ELSE sp.market
            END
        )
        WHERE pp.market = 'batter_hits'
        AND pp.league = 'MLB'
        AND pp.home = %s
        AND pp.away = %s
        AND pp.ou = %s
        AND sp.team_abbr != %s
    """

    cursor.execute(batter_query, (pitcher['home'], pitcher['away'], pitcher['pitcher_ou'], pitcher['pitcher_team']))
    count = cursor.fetchone()['cnt']
    print(f"  > Found {count} opposing batters with matching O/U\n")

# Test 3: Singles correlation
print("\n3. HITS ALLOWED + BATTER SINGLES CORRELATION")
print("-" * 80)

cursor.execute(pitcher_query, ('pitcher_hits_allowed',))
pitchers = cursor.fetchall()

for pitcher in pitchers[:2]:  # Test first 2
    print(f"Pitcher: {pitcher['pitcher_name']} ({pitcher['pitcher_team']}) - {pitcher['pitcher_ou']} {pitcher['pitcher_line']}")

    batter_query = """
        SELECT COUNT(*) as cnt
        FROM player_props pp
        JOIN splash_props sp ON (
            pp.normalized_name = sp.normalized_name
            AND pp.line = sp.line
            AND pp.market = CASE sp.market
                WHEN 'singles' THEN 'batter_singles'
                ELSE sp.market
            END
        )
        WHERE pp.market = 'batter_singles'
        AND pp.league = 'MLB'
        AND pp.home = %s
        AND pp.away = %s
        AND pp.ou = %s
        AND sp.team_abbr != %s
    """

    cursor.execute(batter_query, (pitcher['home'], pitcher['away'], pitcher['pitcher_ou'], pitcher['pitcher_team']))
    count = cursor.fetchone()['cnt']
    print(f"  > Found {count} opposing batters with matching O/U\n")

conn.close()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
