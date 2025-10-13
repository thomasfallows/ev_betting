"""
Database migration to add position_football column to player_props table
This column will store QB, WR1, WR2, WR3, TE, RB for NFL/NCAAF players
"""

import pymysql
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

def add_position_football_column():
    """Add position_football column to player_props table if it doesn't exist"""
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            AND TABLE_NAME = 'player_props'
            AND COLUMN_NAME = 'position_football'
        """, (DB_CONFIG['database'],))

        column_exists = cursor.fetchone()[0] > 0

        if column_exists:
            logger.info("position_football column already exists, skipping")
            return

        # Add the column
        logger.info("Adding position_football column to player_props table...")
        cursor.execute("""
            ALTER TABLE player_props
            ADD COLUMN position_football VARCHAR(10) DEFAULT NULL
            COMMENT 'Football position: QB, WR1, WR2, WR3, TE, RB'
        """)

        conn.commit()
        logger.info("Successfully added position_football column")

        # Create index for faster queries
        logger.info("Creating index on position_football column...")
        cursor.execute("""
            CREATE INDEX idx_position_football
            ON player_props(position_football)
        """)

        conn.commit()
        logger.info("Successfully created index on position_football")

    except pymysql.Error as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Running football position column migration...")
    add_position_football_column()
    print("Migration complete!")
