import pymysql
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

def run_migrations():
    """Run database migrations to ensure all tables have proper structure"""
    logger.info("[Migration] Starting database migrations...")
    
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            logger.info("[Migration] Connected to database")
            
            # Migration 1: Add sport column to splash_props if missing
            logger.info("[Migration] Checking splash_props table...")
            cursor.execute("SHOW COLUMNS FROM splash_props LIKE 'sport'")
            if not cursor.fetchone():
                logger.info("[Migration] Adding 'sport' column to splash_props...")
                cursor.execute("""
                    ALTER TABLE splash_props 
                    ADD COLUMN sport VARCHAR(10) DEFAULT 'mlb' AFTER game_date
                """)
                conn.commit()
                logger.info("[Migration] ✓ Added 'sport' column to splash_props")
            else:
                logger.info("[Migration] ✓ 'sport' column already exists in splash_props")
            
            # Migration 2: Add league column to ev_opportunities if missing
            logger.info("[Migration] Checking ev_opportunities table...")
            cursor.execute("SHOW COLUMNS FROM ev_opportunities LIKE 'league'")
            if not cursor.fetchone():
                logger.info("[Migration] Adding 'league' column to ev_opportunities...")
                cursor.execute("""
                    ALTER TABLE ev_opportunities 
                    ADD COLUMN league VARCHAR(10) DEFAULT NULL AFTER book_count
                """)
                conn.commit()
                logger.info("[Migration] ✓ Added 'league' column to ev_opportunities")
            else:
                logger.info("[Migration] ✓ 'league' column already exists in ev_opportunities")
            
            # Migration 3: Add league column to splash_ev_analysis if missing
            logger.info("[Migration] Checking splash_ev_analysis table...")
            cursor.execute("SHOW COLUMNS FROM splash_ev_analysis LIKE 'league'")
            if not cursor.fetchone():
                logger.info("[Migration] Adding 'league' column to splash_ev_analysis...")
                cursor.execute("""
                    ALTER TABLE splash_ev_analysis 
                    ADD COLUMN league VARCHAR(10) DEFAULT NULL AFTER line
                """)
                conn.commit()
                logger.info("[Migration] ✓ Added 'league' column to splash_ev_analysis")
            else:
                logger.info("[Migration] ✓ 'league' column already exists in splash_ev_analysis")
            
            # Migration 4: Update existing splash_props records based on market type
            logger.info("[Migration] Updating sport values in splash_props based on market types...")
            
            # MLB markets
            mlb_markets = ['pitcher_ks', 'strikeouts', 'earned_runs', 'allowed_hits', 
                          'hits_allowed', 'total_bases', 'hits', 'singles', 'runs', 
                          'rbis', 'outs', 'total_outs']
            
            for market in mlb_markets:
                cursor.execute("""
                    UPDATE splash_props 
                    SET sport = 'mlb' 
                    WHERE market = %s AND sport IS NULL
                """, (market,))
            
            # WNBA markets
            wnba_markets = ['points', 'rebounds', 'pts+reb+asts', 'pts+reb', 'pts+asts']
            
            for market in wnba_markets:
                cursor.execute("""
                    UPDATE splash_props 
                    SET sport = 'wnba' 
                    WHERE market = %s AND (sport IS NULL OR sport = 'mlb')
                """, (market,))
            
            conn.commit()
            logger.info("[Migration] ✓ Updated sport values based on market types")
            
            # Migration 5: Add indexes for better performance
            logger.info("[Migration] Checking indexes...")
            
            # Check and add index on splash_props
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = 'splash_props' 
                AND index_name = 'idx_normalized_name_market_line'
            """)
            
            if cursor.fetchone()[0] == 0:
                logger.info("[Migration] Adding index to splash_props...")
                cursor.execute("""
                    CREATE INDEX idx_normalized_name_market_line 
                    ON splash_props(normalized_name, market, line)
                """)
                conn.commit()
                logger.info("[Migration] ✓ Added index to splash_props")
            else:
                logger.info("[Migration] ✓ Index already exists on splash_props")
            
            # Check and add index on player_props
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = 'player_props' 
                AND index_name = 'idx_normalized_name_market_line'
            """)
            
            if cursor.fetchone()[0] == 0:
                logger.info("[Migration] Adding index to player_props...")
                cursor.execute("""
                    CREATE INDEX idx_normalized_name_market_line 
                    ON player_props(normalized_name, market, line)
                """)
                conn.commit()
                logger.info("[Migration] ✓ Added index to player_props")
            else:
                logger.info("[Migration] ✓ Index already exists on player_props")
            
            # Show summary
            logger.info("[Migration] Summary of table structures:")
            
            # Show splash_props structure
            cursor.execute("DESCRIBE splash_props")
            columns = cursor.fetchall()
            logger.info("[Migration] splash_props columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
            
            # Show ev_opportunities structure
            cursor.execute("DESCRIBE ev_opportunities")
            columns = cursor.fetchall()
            logger.info("[Migration] ev_opportunities columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
            
            # Show splash_ev_analysis structure
            cursor.execute("DESCRIBE splash_ev_analysis")
            columns = cursor.fetchall()
            logger.info("[Migration] splash_ev_analysis columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
            
            logger.info("[Migration] ✓ All migrations completed successfully!")
            
    except pymysql.Error as e:
        logger.error(f"[Migration] Database error: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"[Migration] Unexpected error: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logger.info("[Migration] Database connection closed")

if __name__ == "__main__":
    print("Running Database Migration Script...")
    run_migrations()
    print("Migration script finished.")