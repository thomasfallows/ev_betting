import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

conn = pymysql.connect(
    host='localhost',
    user='root',
    password=os.getenv('DB_PASSWORD'),
    database='MyDatabase'
)

cursor = conn.cursor()

print("\n" + "="*60)
print("SQL TABLES POWERING YOUR FRONTEND")
print("="*60)

cursor.execute('SHOW TABLES')
tables = cursor.fetchall()

for table in tables:
    table_name = table[0]

    # Get row count
    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
    row_count = cursor.fetchone()[0]

    # Get columns
    cursor.execute(f'SHOW COLUMNS FROM {table_name}')
    columns = cursor.fetchall()

    print(f"\n[TABLE] {table_name.upper()}")
    print(f"   Rows: {row_count:,}")
    print(f"   Purpose: ", end="")

    # Describe purpose based on table name
    if table_name == 'player_props':
        print("Stores odds from sportsbooks (DraftKings, FanDuel, etc.)")
    elif table_name == 'splash_props':
        print("Stores available props from Splash Sports")
    elif table_name == 'ev_opportunities':
        print("Calculated +EV betting opportunities")
    elif table_name == 'splash_ev_analysis':
        print("Advanced EV analysis with star player scoring")
    else:
        print("Supporting data")

    print("   Key Columns:")
    for i, col in enumerate(columns):
        if i < 8:  # Show first 8 columns
            print(f"      - {col[0]} ({col[1]})")
        elif i == 8:
            print(f"      ... and {len(columns) - 8} more columns")
            break

print("\n" + "="*60)
print("FRONTEND PAGE MAPPINGS")
print("="*60)

print("""
[HOME] (/) - Dashboard
   -> ev_opportunities: Shows top EV bets
   -> player_props: Counts books and players
   -> splash_ev_analysis: Shows profitable splash bets

[EV OPS] (/ev-opportunities)
   -> ev_opportunities: Main data source
   -> Shows filtered EV opportunities

[ODDS] (/raw-odds)
   -> player_props: Shows all sportsbook odds
   -> Highlights one-sided props

[SINGLES TAB] (in EV OPS)
   -> splash_ev_analysis: Shows single-leg opportunities
   -> Filtered by profitability

[PARLAYS TAB] (in EV OPS)
   -> parlay_opportunities: Would show parlay combos (if table exists)
""")

conn.close()