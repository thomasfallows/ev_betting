import pymysql
from config import DB_CONFIG_DICT

# Connect to database
conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

# Check player_props columns
print("PLAYER_PROPS table structure:")
cursor.execute("DESCRIBE player_props")
for column in cursor.fetchall():
    print(f"  {column}")

print("\nSPLASH_PROPS table structure:")
cursor.execute("DESCRIBE splash_props")
for column in cursor.fetchall():
    print(f"  {column}")

cursor.close()
conn.close()