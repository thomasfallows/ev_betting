import pymysql
from dotenv import load_dotenv
import os
import sys

# Load environment variables
load_dotenv()

# Database connection settings
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD'),
    'database': os.getenv('DB_NAME', 'MyDatabase')
}

def reset_database():
    """
    Complete database reset to match the exact schema expected by the code.
    This will DROP and RECREATE all tables to ensure clean state.
    """
    print("=" * 60)
    print("DATABASE RESET SCRIPT")
    print("WARNING: This will DROP and RECREATE all betting tables!")
    print("=" * 60)

    response = input("\nAre you sure you want to reset the database? (yes/no): ")
    if response.lower() != 'yes':
        print("Database reset cancelled.")
        return

    conn = None
    try:
        # Connect to database
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print(f"\nConnected to database: {DB_CONFIG['database']}")

        # Drop existing tables
        print("\nDropping existing tables...")
        tables_to_drop = [
            'ev_opportunities',
            'player_props',
            'splash_props',
            'ev_report',  # Legacy table
            'historical_data',  # If exists
            'parlay_opportunities'  # Future use
        ]

        for table in tables_to_drop:
            try:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"  ✓ Dropped table: {table}")
            except Exception as e:
                print(f"  ⚠ Could not drop {table}: {e}")

        # Create tables with correct schema
        print("\nCreating tables with correct schema...")

        # 1. splash_props table
        cursor.execute("""
            CREATE TABLE splash_props (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(255) COLLATE utf8mb4_general_ci,
                normalized_name VARCHAR(255) COLLATE utf8mb4_general_ci,
                market VARCHAR(100),
                line DECIMAL(10,2),
                game_date DATETIME,
                home VARCHAR(255),
                away VARCHAR(255),
                sport VARCHAR(10) DEFAULT 'mlb',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_player_market_line (normalized_name, market, line),
                INDEX idx_sport (sport),
                INDEX idx_game_date (game_date)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
        """)
        print("  ✓ Created table: splash_props")

        # 2. player_props table
        cursor.execute("""
            CREATE TABLE player_props (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(255) COLLATE utf8mb4_general_ci,
                normalized_name VARCHAR(255) COLLATE utf8mb4_general_ci,
                market VARCHAR(100),
                line DECIMAL(10,2),
                ou VARCHAR(1),
                book VARCHAR(50),
                dxodds INT,
                home VARCHAR(255),
                away VARCHAR(255),
                game_id VARCHAR(255),
                sport VARCHAR(10) DEFAULT 'mlb',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_player_market_line_ou (normalized_name, market, line, ou),
                INDEX idx_book (book),
                INDEX idx_sport (sport)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
        """)
        print("  ✓ Created table: player_props")

        # 3. ev_opportunities table (CRITICAL - this is where the error was)
        cursor.execute("""
            CREATE TABLE ev_opportunities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                player_name VARCHAR(255) COLLATE utf8mb4_general_ci,
                ou VARCHAR(1),
                market_type VARCHAR(100),  -- THIS COLUMN WAS MISSING!
                home_team VARCHAR(255),
                away_team VARCHAR(255),
                line DECIMAL(10,2),
                ev_percentage DECIMAL(10,4),
                book_count INT,
                league VARCHAR(10) DEFAULT 'mlb',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ev (ev_percentage),
                INDEX idx_player (player_name),
                INDEX idx_market (market_type)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
        """)
        print("  ✓ Created table: ev_opportunities")

        # 4. Historical data table (for backtesting)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_data (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date_collected DATETIME,
                player_name VARCHAR(255),
                market VARCHAR(100),
                line DECIMAL(10,2),
                ou VARCHAR(1),
                book VARCHAR(50),
                odds INT,
                splash_available BOOLEAN,
                ev_percentage DECIMAL(10,4),
                sport VARCHAR(10) DEFAULT 'mlb',
                INDEX idx_date (date_collected),
                INDEX idx_player_market (player_name, market)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
        """)
        print("  ✓ Created table: historical_data")

        # 5. Future parlay tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parlay_opportunities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                contest_type VARCHAR(10),
                parlay_probability DECIMAL(10,6),
                ev_percentage DECIMAL(10,4),
                leg1_player VARCHAR(255),
                leg1_market VARCHAR(100),
                leg1_line DECIMAL(10,2),
                leg1_ou VARCHAR(1),
                leg2_player VARCHAR(255),
                leg2_market VARCHAR(100),
                leg2_line DECIMAL(10,2),
                leg2_ou VARCHAR(1),
                leg3_player VARCHAR(255),
                leg3_market VARCHAR(100),
                leg3_line DECIMAL(10,2),
                leg3_ou VARCHAR(1),
                leg4_player VARCHAR(255),
                leg4_market VARCHAR(100),
                leg4_line DECIMAL(10,2),
                leg4_ou VARCHAR(1),
                leg5_player VARCHAR(255),
                leg5_market VARCHAR(100),
                leg5_line DECIMAL(10,2),
                leg5_ou VARCHAR(1),
                leg6_player VARCHAR(255),
                leg6_market VARCHAR(100),
                leg6_line DECIMAL(10,2),
                leg6_ou VARCHAR(1),
                correlation_score DECIMAL(5,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_contest_ev (contest_type, ev_percentage)
            ) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci
        """)
        print("  ✓ Created table: parlay_opportunities")

        conn.commit()

        print("\n" + "=" * 60)
        print("DATABASE RESET COMPLETE!")
        print("=" * 60)
        print("\nAll tables have been recreated with the correct schema.")
        print("The 'market_type' column is now present in ev_opportunities.")
        print("\nNext steps:")
        print("1. Run: python Backend/data_scripts/splash_scraper.py")
        print("2. Run: python Backend/data_scripts/odds_api.py")
        print("3. Run: python Backend/data_scripts/create_report.py")
        print("4. Access the web interface at http://localhost:5001")

    except pymysql.err.OperationalError as e:
        if "Access denied" in str(e):
            print(f"\n❌ Database connection failed!")
            print(f"   Error: {e}")
            print(f"\n   Please check your .env file has the correct password.")
            print(f"   Current password in .env: {DB_CONFIG['password']}")
        else:
            print(f"\n❌ Database error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("\nDatabase connection closed.")

if __name__ == "__main__":
    reset_database()