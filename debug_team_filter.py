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

# Get pitcher team from the join
cursor.execute("""
    SELECT DISTINCT
        pp.Player as pitcher_name,
        sp.team_abbr as pitcher_team
    FROM player_props pp
    JOIN splash_props sp ON (
        pp.normalized_name = sp.normalized_name
        AND pp.line = sp.line
        AND pp.market = CASE sp.market
            WHEN 'hits_allowed' THEN 'pitcher_hits_allowed'
            ELSE sp.market
        END
    )
    WHERE pp.Player = 'Jesus Luzardo'
    AND pp.market = 'pitcher_hits_allowed'
""")
result = cursor.fetchone()

if result:
    print(f"Pitcher team from JOIN: '{result['pitcher_team']}'")

    # Now run the batter query with the != filter
    cursor.execute("""
        SELECT DISTINCT
            pp.Player as batter_name,
            sp.team_abbr as batter_team
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
        AND pp.home = 'Philadelphia Phillies'
        AND pp.away = 'Los Angeles Dodgers'
        AND pp.ou = 'O'
        AND sp.team_abbr != %s
        LIMIT 10
    """, (result['pitcher_team'],))

    batters = cursor.fetchall()
    print(f"\nOpposing batters (team != '{result['pitcher_team']}'): {len(batters)}")
    for b in batters:
        print(f"  {b['batter_name']:25s} | Team: '{b['batter_team']}'")

conn.close()
