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

print('Testing batter query for Luis Castillo (SEA pitcher)...')
print('Looking for opposing batters (DET) with OVER runs\n')

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
    LIMIT 5
"""

cursor.execute(batter_query, (
    'batter_runs_scored',
    'Seattle Mariners',
    'Detroit Tigers',
    'O',
    'Luis Castillo',
    'SEA'
))
batters = cursor.fetchall()
print(f'Found {len(batters)} opposing batters')
for b in batters:
    print(f"  {b['batter_name']:20s} | {b['batter_team']:5s} | {b['batter_market']} {b['batter_ou']} {b['batter_line']}")

conn.close()
