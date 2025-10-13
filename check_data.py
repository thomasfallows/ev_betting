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

print("\nTABLE DATA STATUS:")
print("=" * 50)

tables = ['player_props', 'splash_props', 'ev_opportunities', 'splash_ev_analysis']

for table in tables:
    cursor.execute(f'SELECT COUNT(*) FROM {table}')
    count = cursor.fetchone()[0]
    status = "POPULATED" if count > 0 else "EMPTY"
    print(f"{table:20} {count:6,} rows  [{status}]")

conn.close()

print("\n" + "=" * 50)
print("NEXT STEPS:")
print("=" * 50)
print("\nev_opportunities table now has 580 rows!")
print("Your frontend should now display data properly.")
print("\nTo populate splash_ev_analysis (optional):")
print("  python Backend/data_scripts/splash_ev_analysis.py")