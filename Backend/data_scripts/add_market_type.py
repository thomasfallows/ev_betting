import pymysql
from dotenv import load_dotenv
import os

load_dotenv()

# Database connection
conn = pymysql.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    user=os.getenv('DB_USER', 'root'),
    password=os.getenv('DB_PASSWORD'),
    database=os.getenv('DB_NAME', 'MyDatabase')
)

cursor = conn.cursor()

try:
    # Add market_type column to each table if it doesn't exist
    tables = ['ev_opportunities', 'player_props', 'splash_props']

    for table in tables:
        try:
            cursor.execute(f"""
                ALTER TABLE {table}
                ADD COLUMN market_type VARCHAR(10) DEFAULT 'single'
            """)
            print(f"Added market_type column to {table}")
        except pymysql.err.OperationalError as e:
            if "Duplicate column name" in str(e):
                print(f"Column market_type already exists in {table}")
            else:
                raise e

    conn.commit()
    print("\nDatabase migration completed successfully!")

except Exception as e:
    print(f"Error during migration: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()