import pymysql
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

def run_parlay_migrations():
    """Add parlay tracking columns to ev_opportunities table"""
    logger.info("[Parlay Migration] Starting parlay tracking migrations...")
    
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            logger.info("[Parlay Migration] Connected to database")
            
            # Check and add contest_type column
            logger.info("[Parlay Migration] Checking for contest_type column...")
            cursor.execute("SHOW COLUMNS FROM ev_opportunities LIKE 'contest_type'")
            if not cursor.fetchone():
                logger.info("[Parlay Migration] Adding 'contest_type' column...")
                cursor.execute("""
                    ALTER TABLE ev_opportunities 
                    ADD COLUMN contest_type VARCHAR(10) DEFAULT '2-man' AFTER ev_percentage
                """)
                conn.commit()
                logger.info("[Parlay Migration] ✓ Added 'contest_type' column")
            else:
                logger.info("[Parlay Migration] ✓ 'contest_type' column already exists")
            
            # Check and add parlay_probability column
            logger.info("[Parlay Migration] Checking for parlay_probability column...")
            cursor.execute("SHOW COLUMNS FROM ev_opportunities LIKE 'parlay_probability'")
            if not cursor.fetchone():
                logger.info("[Parlay Migration] Adding 'parlay_probability' column...")
                cursor.execute("""
                    ALTER TABLE ev_opportunities 
                    ADD COLUMN parlay_probability DECIMAL(10,6) AFTER contest_type
                """)
                conn.commit()
                logger.info("[Parlay Migration] ✓ Added 'parlay_probability' column")
            else:
                logger.info("[Parlay Migration] ✓ 'parlay_probability' column already exists")
            
            # Check and add contest_ev_percent column
            logger.info("[Parlay Migration] Checking for contest_ev_percent column...")
            cursor.execute("SHOW COLUMNS FROM ev_opportunities LIKE 'contest_ev_percent'")
            if not cursor.fetchone():
                logger.info("[Parlay Migration] Adding 'contest_ev_percent' column...")
                cursor.execute("""
                    ALTER TABLE ev_opportunities 
                    ADD COLUMN contest_ev_percent DECIMAL(10,6) AFTER parlay_probability
                """)
                conn.commit()
                logger.info("[Parlay Migration] ✓ Added 'contest_ev_percent' column")
            else:
                logger.info("[Parlay Migration] ✓ 'contest_ev_percent' column already exists")
            
            # Check and add break_even_probability column
            logger.info("[Parlay Migration] Checking for break_even_probability column...")
            cursor.execute("SHOW COLUMNS FROM ev_opportunities LIKE 'break_even_probability'")
            if not cursor.fetchone():
                logger.info("[Parlay Migration] Adding 'break_even_probability' column...")
                cursor.execute("""
                    ALTER TABLE ev_opportunities 
                    ADD COLUMN break_even_probability DECIMAL(10,6) AFTER contest_ev_percent
                """)
                conn.commit()
                logger.info("[Parlay Migration] ✓ Added 'break_even_probability' column")
            else:
                logger.info("[Parlay Migration] ✓ 'break_even_probability' column already exists")
            
            # Check and add edge_over_breakeven column
            logger.info("[Parlay Migration] Checking for edge_over_breakeven column...")
            cursor.execute("SHOW COLUMNS FROM ev_opportunities LIKE 'edge_over_breakeven'")
            if not cursor.fetchone():
                logger.info("[Parlay Migration] Adding 'edge_over_breakeven' column...")
                cursor.execute("""
                    ALTER TABLE ev_opportunities 
                    ADD COLUMN edge_over_breakeven DECIMAL(10,6) AFTER break_even_probability
                """)
                conn.commit()
                logger.info("[Parlay Migration] ✓ Added 'edge_over_breakeven' column")
            else:
                logger.info("[Parlay Migration] ✓ 'edge_over_breakeven' column already exists")
            
            # Create new parlays table for tracking complete parlays
            logger.info("[Parlay Migration] Checking for parlays table...")
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'parlays'
            """)
            
            if cursor.fetchone()[0] == 0:
                logger.info("[Parlay Migration] Creating 'parlays' table...")
                cursor.execute("""
                    CREATE TABLE parlays (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        contest_type VARCHAR(10) NOT NULL DEFAULT '2-man',
                        parlay_hash VARCHAR(64) NOT NULL UNIQUE,
                        leg_count INT NOT NULL,
                        parlay_probability DECIMAL(10,6) NOT NULL,
                        contest_ev_percent DECIMAL(10,6) NOT NULL,
                        break_even_probability DECIMAL(10,6) NOT NULL,
                        edge_over_breakeven DECIMAL(10,6) NOT NULL,
                        meets_minimum BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_contest_type (contest_type),
                        INDEX idx_ev_percent (contest_ev_percent DESC),
                        INDEX idx_created_at (created_at)
                    )
                """)
                conn.commit()
                logger.info("[Parlay Migration] ✓ Created 'parlays' table")
            else:
                logger.info("[Parlay Migration] ✓ 'parlays' table already exists")
            
            # Create parlay_legs table to store individual legs of each parlay
            logger.info("[Parlay Migration] Checking for parlay_legs table...")
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'parlay_legs'
            """)
            
            if cursor.fetchone()[0] == 0:
                logger.info("[Parlay Migration] Creating 'parlay_legs' table...")
                cursor.execute("""
                    CREATE TABLE parlay_legs (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        parlay_hash VARCHAR(64) NOT NULL,
                        leg_number INT NOT NULL,
                        player_name VARCHAR(200) NOT NULL,
                        normalized_name VARCHAR(200) NOT NULL,
                        market VARCHAR(100) NOT NULL,
                        line DECIMAL(10,2) NOT NULL,
                        ou VARCHAR(10) NOT NULL,
                        true_probability DECIMAL(10,6) NOT NULL,
                        sport VARCHAR(10) DEFAULT 'mlb',
                        game_id VARCHAR(100),
                        INDEX idx_parlay_hash (parlay_hash),
                        INDEX idx_player_market (normalized_name, market),
                        FOREIGN KEY (parlay_hash) REFERENCES parlays(parlay_hash) ON DELETE CASCADE
                    )
                """)
                conn.commit()
                logger.info("[Parlay Migration] ✓ Created 'parlay_legs' table")
            else:
                logger.info("[Parlay Migration] ✓ 'parlay_legs' table already exists")
            
            # Show summary of new structure
            logger.info("[Parlay Migration] Summary of updated table structures:")
            
            # Show ev_opportunities structure
            cursor.execute("DESCRIBE ev_opportunities")
            columns = cursor.fetchall()
            logger.info("[Parlay Migration] ev_opportunities columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
            
            # Show parlays structure
            cursor.execute("DESCRIBE parlays")
            columns = cursor.fetchall()
            logger.info("[Parlay Migration] parlays columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
            
            # Show parlay_legs structure
            cursor.execute("DESCRIBE parlay_legs")
            columns = cursor.fetchall()
            logger.info("[Parlay Migration] parlay_legs columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
            
            logger.info("[Parlay Migration] ✓ All parlay migrations completed successfully!")
            
    except pymysql.Error as e:
        logger.error(f"[Parlay Migration] Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[Parlay Migration] Unexpected error: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("[Parlay Migration] Database connection closed")

if __name__ == "__main__":
    print("Running Parlay Migration Script...")
    run_parlay_migrations()
    print("Parlay migration script finished.")