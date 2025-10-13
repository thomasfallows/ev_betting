import pymysql
from dotenv import load_dotenv
import os

# Load environment variables
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
    # First, check what columns exist in ev_opportunities
    print("Checking current columns in ev_opportunities table...")
    cursor.execute("SHOW COLUMNS FROM ev_opportunities")
    columns = cursor.fetchall()

    print("\nCurrent columns:")
    column_names = []
    for col in columns:
        print(f"  - {col[0]} ({col[1]})")
        column_names.append(col[0])

    # Check if market_type exists
    if 'market_type' not in column_names:
        print("\n❌ 'market_type' column is MISSING! Adding it now...")
        cursor.execute("""
            ALTER TABLE ev_opportunities
            ADD COLUMN market_type VARCHAR(100) AFTER ou
        """)
        conn.commit()
        print("✓ Added 'market_type' column successfully!")
    else:
        print("\n✓ 'market_type' column already exists!")

    # Verify the fix
    cursor.execute("SHOW COLUMNS FROM ev_opportunities")
    columns = cursor.fetchall()
    print("\nUpdated columns:")
    for col in columns:
        print(f"  - {col[0]} ({col[1]})")

    print("\n✅ Database fix complete! The frontend should work now.")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()