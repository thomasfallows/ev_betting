import os
import pymysql
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# --- API and Database Credentials ---
API_KEY = os.getenv("ODDS_API_KEY")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME", "MyDatabase")

# --- Application Settings ---
# Support MLB, WNBA, NFL, and NCAAF
SPORTS_CONFIG = {
    'mlb': {
        'base_url': "https://api.the-odds-api.com/v4/sports/baseball_mlb",
        'markets': ",".join([
            "pitcher_strikeouts",    # Pitcher Ks
            "pitcher_earned_runs",   # Earned Runs
            "pitcher_hits_allowed",  # Allowed Hits
            "batter_total_bases",    # Total Bases
            "batter_hits",           # Hits
            "batter_singles",        # Singles
            "batter_runs_scored",    # Runs
            "batter_rbis",           # RBIs
            "pitcher_outs"           # Outs
        ])
    },
    'wnba': {
        'base_url': "https://api.the-odds-api.com/v4/sports/basketball_wnba",
        'markets': ",".join([
            "player_points",                    # Points
            "player_rebounds",                  # Rebounds
            "player_assists",                   # Assists
            "player_points_rebounds_assists",   # Pts+Reb+Asts
            "player_points_rebounds",           # Pts+Reb
            "player_points_assists"             # Pts+Asts
        ])
    },
    'nfl': {
        'base_url': "https://api.the-odds-api.com/v4/sports/americanfootball_nfl",
        'markets': ",".join([
            "player_pass_yds",           # Pass Yards
            "player_pass_completions",   # Pass Completions
            "player_reception_yds",      # Reception Yards
            "player_receptions"          # Receptions (NEW - for completions correlation)
        ])
    },
    'ncaaf': {
        'base_url': "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf",
        'markets': ",".join([
            "player_pass_yds",           # Pass Yards (QB anchor)
            "player_reception_yds",      # Reception Yards (WR/TE/RB)
            "player_receptions"          # Receptions (WR/TE/RB) - Splash has Rec but not Pass Comp for NCAAF
        ])
    }
}

REGION = "us"  # Temporarily using only US region to reduce API costs by 50% during testing
US_ONLY = True
US_KEYWORDS = ("draftkings", "fanduel", "caesars", "betmgm", "pointsbet", "bet365", "espnbet", "betrivers", "fanatics")
LOCAL_TZ_STR = "America/Halifax"

# --- Database Configuration Dictionaries ---
# For PyMySQL without DictCursor (used in scripts)
DB_CONFIG = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME
}

# For PyMySQL with DictCursor (used in Flask app)
DB_CONFIG_DICT = {
    "host": DB_HOST,
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "cursorclass": pymysql.cursors.DictCursor
}

# --- Market Name Mapping ---
# Maps Splash Sports market names to The Odds API market names
MARKET_MAP = {
    # MLB Markets
    'pitcher_ks': 'pitcher_strikeouts',
    'strikeouts': 'pitcher_strikeouts',
    'earned_runs': 'pitcher_earned_runs',
    'allowed_hits': 'pitcher_hits_allowed',
    'hits_allowed': 'pitcher_hits_allowed',
    'total_bases': 'batter_total_bases',
    'hits': 'batter_hits',
    'singles': 'batter_singles',
    'runs': 'batter_runs_scored',
    'rbis': 'batter_rbis',
    'outs': 'pitcher_outs',
    'total_outs': 'pitcher_outs',
    
    # WNBA Markets - Updated with correct Splash names
    'points': 'player_points',
    'rebounds': 'player_rebounds',
    'assists': 'player_assists',
    'points_plus_assists_plus_rebounds': 'player_points_rebounds_assists',
    'points_plus_rebounds': 'player_points_rebounds',
    'points_plus_assists': 'player_points_assists',
    'assists_plus_rebounds': 'player_assists_rebounds',
    
    # Alternative WNBA naming
    'pts+reb+asts': 'player_points_rebounds_assists',
    'pts+reb': 'player_points_rebounds',
    'pts+asts': 'player_points_assists',
    'asts+reb': 'player_assists_rebounds',

    # NFL/NCAAF Markets - Splash naming to API naming
    'passing_yards': 'player_pass_yds',
    'completions': 'player_pass_completions',
    'receiving_yards': 'player_reception_yds',
    'receiving_receptions': 'player_receptions'
}

# Star players for public appeal scoring
STAR_PLAYERS = {
    # MLB Stars
    'Aaron Judge', 'Mookie Betts', 'Juan Soto', 'Fernando Tatis Jr.', 
    'Ronald Acuna Jr.', 'Mike Trout', 'Manny Machado', 'Francisco Lindor',
    'Freddie Freeman', 'Vladimir Guerrero Jr.', 'Jose Altuve', 'Bryce Harper',
    'Gerrit Cole', 'Jacob deGrom', 'Shane Bieber', 'Sandy Alcantara',
    
    # WNBA Stars (adding major stars - will refine as we learn)
    'A\'ja Wilson', 'Breanna Stewart', 'Diana Taurasi', 'Sue Bird',
    'Candace Parker', 'Sabrina Ionescu', 'Kelsey Plum', 'Alyssa Thomas',
    'Jewell Loyd', 'Skylar Diggins-Smith', 'Courtney Vandersloot', 'Nneka Ogwumike'
}