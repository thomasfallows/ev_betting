import pymysql
from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sys
import os
import urllib.parse
import re
from decimal import Decimal

# Add path for config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT

# Import data collection scripts with error handling
run_splash_scraper_script = None
run_odds_api_script = None
run_create_report_script = None
run_parlay_report_script = None
run_splash_ev_analysis_script = None

try:
    from data_scripts.splash_scraper import run_splash_scraper_script
    from data_scripts.odds_api import run_splash_driven_odds_collection as run_odds_api_script
    from data_scripts.create_report import run_create_report_script
    from data_scripts.create_report_parlay import run_parlay_report as run_parlay_report_script
    # Fix: Import the actual function, not a circular import
    from data_scripts.splash_ev_analysis import run_splash_ev_analysis
    run_splash_ev_analysis_script = run_splash_ev_analysis
    print("Successfully imported all data scripts")
except Exception as e:
    print(f"Import error: {e}")
    import traceback
    traceback.print_exc()

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'ev_betting_2024_secure_key_change_in_production'

# User credentials (hashed)
USERS = {
    'tfal': generate_password_hash('Mfitnt4eip')
}

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_bloomberg_css():
    """Bloomberg Terminal CSS styling - Authentic Orange/Black"""
    return '''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@300;400;500;700&display=swap');
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Roboto Mono', monospace;
            background: #000000;
            color: #ff8c00;
            margin: 0;
            padding: 0;
            overflow-x: auto;
        }
        
        .terminal-container {
            background: #000000;
            border: 2px solid #ff8c00;
            margin: 10px;
            padding: 0;
            min-height: calc(100vh - 20px);
        }
        
        .terminal-header {
            background: #1a1a1a;
            border-bottom: 1px solid #ff8c00;
            padding: 8px 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 10px;
        }
        
        .terminal-title {
            color: #ff8c00;
            font-weight: 700;
            font-size: 14px;
            letter-spacing: 1px;
            text-transform: uppercase;
        }
        
        .terminal-nav {
            display: flex;
            gap: 2px;
        }
        
        .nav-btn {
            background: #000000;
            color: #ff8c00;
            border: 1px solid #ff8c00;
            padding: 6px 12px;
            font-family: 'Roboto Mono', monospace;
            font-size: 11px;
            font-weight: 500;
            text-decoration: none;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .nav-btn:hover, .nav-btn.active {
            background: #ff8c00;
            color: #000000;
        }
        
        .update-btn {
            background: #ff8c00;
            color: #000000;
            border: 1px solid #ff8c00;
            font-weight: 700;
        }
        
        .update-btn:hover {
            background: #000000;
            color: #ff8c00;
        }
        
        .update-btn:disabled {
            background: #333333;
            color: #666666;
            border-color: #333333;
            cursor: not-allowed;
        }
        
        .terminal-content {
            padding: 15px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .stat-box {
            background: #1a1a1a;
            border: 1px solid #ff8c00;
            padding: 10px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 18px;
            font-weight: 700;
            color: #ff8c00;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 10px;
            color: #cc7000;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .controls {
            margin: 15px 0;
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }
        
        .pagination {
            display: flex;
            gap: 5px;
            align-items: center;
            margin-left: auto;
        }
        
        .page-btn {
            background: #000000;
            color: #ff8c00;
            border: 1px solid #ff8c00;
            padding: 6px 10px;
            font-family: 'Roboto Mono', monospace;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .page-btn:hover:not(:disabled) {
            background: #ff8c00;
            color: #000000;
        }
        
        .page-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .page-btn.active {
            background: #ff8c00;
            color: #000000;
        }
        
        .page-info {
            color: #ff8c00;
            font-size: 11px;
            margin: 0 10px;
        }
        
        .search-input {
            background: #000000;
            border: 1px solid #ff8c00;
            color: #ff8c00;
            padding: 6px 10px;
            font-family: 'Roboto Mono', monospace;
            font-size: 11px;
            width: 200px;
        }
        
        .search-input::placeholder {
            color: #cc7000;
        }
        
        .filter-input {
            background: #000000;
            border: 1px solid #ff8c00;
            color: #ff8c00;
            padding: 6px 10px;
            font-family: 'Roboto Mono', monospace;
            font-size: 11px;
            width: 80px;
            text-align: center;
        }
        
        .filter-input::placeholder {
            color: #cc7000;
        }
        
        .tab-container {
            display: flex;
            gap: 0;
            margin: 15px 0 20px 0;
            border-bottom: 2px solid #ff8c00;
        }
        
        .tab-btn {
            background: #000000;
            color: #cc7000;
            border: 1px solid #ff8c00;
            border-bottom: none;
            padding: 10px 20px;
            font-family: 'Roboto Mono', monospace;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            text-transform: uppercase;
            letter-spacing: 1px;
            position: relative;
            top: 2px;
        }
        
        .tab-btn:hover {
            background: #1a1a1a;
            color: #ff8c00;
        }
        
        .tab-btn.active {
            background: #000000;
            color: #ff8c00;
            border-bottom: 2px solid #000000;
            font-weight: 700;
        }
        
        .parlay-card {
            background: #000000;
            border: 2px solid #ff8c00;
            margin: 15px 0;
            padding: 20px;
            position: relative;
            transition: all 0.2s;
        }
        
        .parlay-card:hover {
            border-color: #ffaa33;
            box-shadow: 0 0 10px rgba(255, 140, 0, 0.3);
        }
        
        .parlay-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #ff8c00;
        }
        
        .contest-type {
            font-size: 14px;
            font-weight: 700;
            color: #ffaa33;
            text-transform: uppercase;
        }
        
        .ev-display {
            font-size: 24px;
            font-weight: 700;
            color: #90ee90;
        }
        
        .parlay-metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .metric-item {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        
        .metric-label {
            font-size: 10px;
            color: #cc7000;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .metric-value {
            font-size: 16px;
            font-weight: 600;
            color: #ff8c00;
        }
        
        .parlay-legs {
            margin-top: 20px;
        }
        
        .leg-card {
            background: #1a1a1a;
            border: 1px solid #ff8c00;
            padding: 15px;
            margin: 10px 0;
        }
        
        .leg-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }
        
        .leg-player {
            font-weight: 600;
            color: #ffaa33;
        }
        
        .leg-details {
            color: #ff8c00;
            font-size: 12px;
        }
        
        .filter-group {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .filter-label {
            color: #ff8c00;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .apply-filters-btn {
            background: #000000;
            color: #90ee90;
            border: 1px solid #90ee90;
            padding: 6px 12px;
            font-family: 'Roboto Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            text-transform: uppercase;
            transition: all 0.2s;
        }
        
        .apply-filters-btn:hover {
            background: #90ee90;
            color: #000000;
        }
        
        .filter-btn {
            background: #000000;
            color: #ff8c00;
            border: 1px solid #ff8c00;
            padding: 6px 12px;
            font-family: 'Roboto Mono', monospace;
            font-size: 10px;
            font-weight: 500;
            text-transform: uppercase;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .filter-btn.active {
            background: #ff8c00;
            color: #000000;
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-top: 10px;
        }
        
        .data-table th {
            background: #1a1a1a;
            color: #ff8c00;
            padding: 8px 6px;
            text-align: center;
            border: 1px solid #ff8c00;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 10px;
        }
        
        .data-table td {
            padding: 6px;
            border: 1px solid #444444;
            text-align: center;
            font-weight: 400;
            color: #ff8c00;
        }
        
        .data-table tr:nth-child(even) {
            background: #0a0a0a;
        }
        
        .data-table tr:hover {
            background: #1a1a1a;
        }
        
        /* EV Color Coding - Bloomberg Style with Subtle Colors */
        .ev-prime {
            background: #2d4a2d !important;
            color: #ffffff;
            font-weight: 700;
        }
        
        .ev-good {
            background: #1f3a1f !important;
            color: #ffffff;
            font-weight: 700;
        }
        
        .ev-marginal {
            background: #1a1a1a !important;
            color: #ff8c00;
            font-weight: 500;
        }
        
        .ev-negative {
            background: #3d1a1a !important;
            color: #ffffff;
            font-weight: 500;
        }
        
        /* Appeal Score Colors */
        .appeal-low {
            color: #90ee90;
            font-weight: 700;
        }
        
        .appeal-medium {
            color: #ff8c00;
            font-weight: 700;
        }
        
        .appeal-high {
            color: #ff6666;
            font-weight: 700;
        }
        
        /* League Colors */
        .league-mlb {
            color: #ff8c00;
            font-weight: 500;
        }
        
        .league-wnba {
            color: #ffaa44;
            font-weight: 500;
        }
        
        /* Player Names */
        .player-name {
            text-align: left;
            font-weight: 700;
            color: #ffffff;
        }
        
        /* League Column */
        .league-col {
            color: #ff8c00;
            font-weight: 600;
            text-align: center;
        }
        
        /* Side Indicators */
        .side-over {
            color: #90ee90;
            font-weight: 700;
        }
        
        .side-under {
            color: #ff6666;
            font-weight: 700;
        }
        
        /* Strategy Indicators */
        .strategy-prime {
            color: #90ee90;
            font-weight: 700;
        }
        
        .strategy-good {
            color: #98d982;
            font-weight: 700;
        }
        
        .strategy-marginal {
            color: #ff8c00;
            font-weight: 700;
        }
        
        /* Clickable odds styling */
        .odds-link {
            color: #ff8c00;
            text-decoration: none;
            padding: 2px 4px;
            border: 1px solid transparent;
            border-radius: 3px;
            transition: all 0.2s;
            font-weight: 500;
        }
        
        .odds-link:hover {
            background: #ff8c00;
            color: #000000;
            border-color: #ff8c00;
        }
        
        .odds-positive {
            color: #90ee90;
        }
        
        .odds-negative {
            color: #ff6666;
        }
        
        /* One-sided prop styling */
        .one-sided-prop {
            background: #4d4d00 !important;  /* Dark yellow */
            opacity: 0.8;
        }
        
        .one-sided-prop:hover {
            background: #666600 !important;
        }
        
        .progress-container {
            margin: 10px 0;
            display: none;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: #000000;
            border: 1px solid #ff8c00;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: #ff8c00;
            width: 0%;
            transition: width 0.3s;
        }
        
        .progress-text {
            color: #ff8c00;
            font-size: 10px;
            margin-top: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .info-panel {
            background: #1a1a1a;
            border: 1px solid #ff8c00;
            padding: 12px;
            margin: 15px 0;
            font-size: 10px;
            line-height: 1.4;
            color: #ff8c00;
        }
        
        .info-panel strong {
            color: #ffffff;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .terminal-header {
                flex-direction: column;
                align-items: stretch;
            }
            
            .terminal-nav {
                justify-content: center;
                flex-wrap: wrap;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
            
            .controls {
                flex-direction: column;
                align-items: stretch;
            }
            
            .data-table {
                font-size: 9px;
            }
            
            .data-table th,
            .data-table td {
                padding: 4px 2px;
            }
        }
    </style>
    '''

def safe_float(value, default=0):
    """Safely convert value to float"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Safely convert value to int"""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def american_to_prob(odds):
    """Convert American odds to implied probability"""
    if odds is None:
        return None
    try:
        odds = float(odds)
        if odds < 0:
            return abs(odds) / (abs(odds) + 100)
        else:
            return 100 / (odds + 100)
    except (ValueError, TypeError):
        return None

def calculate_ev_from_odds(odds_list):
    """Calculate EV% from a list of American odds"""
    if not odds_list or len(odds_list) == 0:
        return None
    
    # Convert odds to probabilities
    probs = []
    for odds in odds_list:
        prob = american_to_prob(odds)
        if prob is not None:
            probs.append(prob)
    
    if not probs:
        return None
    
    # Calculate average probability (fair odds)
    avg_prob = sum(probs) / len(probs)
    
    # Splash implied probability
    splash_prob = 0.5774  # (1/3)^(1/2)
    
    # Calculate EV%
    ev_percentage = (avg_prob - splash_prob) * 100
    
    return ev_percentage

def calculate_devigged_ev(books_data):
    """Calculate de-vigged EV% from books data with both sides"""
    # Group odds by book
    book_odds = {}
    
    for book, odds, ou in books_data:
        if book not in book_odds:
            book_odds[book] = {}
        book_odds[book][ou] = odds
    
    # Find books with both sides and calculate de-vigged probabilities
    valid_book_probs = []
    
    for book, odds in book_odds.items():
        if 'O' in odds and 'U' in odds:
            over_prob = american_to_prob(odds['O'])
            under_prob = american_to_prob(odds['U'])
            
            if over_prob is None or under_prob is None:
                continue
                
            # Calculate total (includes vig)
            total = over_prob + under_prob
            
            # De-vigged probabilities
            true_over_prob = over_prob / total
            true_under_prob = under_prob / total
            
            valid_book_probs.append({
                'book': book,
                'over_prob': true_over_prob,
                'under_prob': true_under_prob
            })
    
    if not valid_book_probs:
        return None, False
    
    # Average de-vigged probabilities across all valid books
    avg_over_prob = sum(b['over_prob'] for b in valid_book_probs) / len(valid_book_probs)
    avg_under_prob = sum(b['under_prob'] for b in valid_book_probs) / len(valid_book_probs)
    
    # Splash implied probability
    splash_prob = 0.5774  # (1/3)^(1/2)
    
    # Calculate EV% for both sides
    ev_over = (avg_over_prob - splash_prob) * 100
    ev_under = (avg_under_prob - splash_prob) * 100
    
    return {'O': ev_over, 'U': ev_under}, True

def normalize_player_for_url(player_name):
    """Normalize player name for URL usage"""
    name = player_name.lower()
    name = re.sub(r'[áàâã]', 'a', name)
    name = re.sub(r'[éèêë]', 'e', name)
    name = re.sub(r'[íìîï]', 'i', name)
    name = re.sub(r'[óòôõ]', 'o', name)
    name = re.sub(r'[úùûü]', 'u', name)
    name = re.sub(r'[ñ]', 'n', name)
    name = re.sub(r'[ç]', 'c', name)
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def build_sportsbook_url(book_name, player_name, market_type):
    """Build URL to sportsbook with player search"""
    normalized_name = normalize_player_for_url(player_name)
    encoded_name = urllib.parse.quote_plus(normalized_name)
    
    if "fanduel" in book_name.lower():
        return f"https://sportsbook.fanduel.com/navigation/mlb?search={encoded_name}"
    elif "draftkings" in book_name.lower():
        return f"https://sportsbook.draftkings.com/leagues/baseball/mlb?search={encoded_name}"
    elif "betmgm" in book_name.lower():
        return f"https://sports.betmgm.com/en/sports/baseball-23/betting/usa-9/mlb-75?search={encoded_name}"
    elif "caesars" in book_name.lower():
        return f"https://sportsbook.caesars.com/us/co/bet/baseball?search={encoded_name}"
    elif "betrivers" in book_name.lower():
        return f"https://co.betrivers.com/?page=sportsbook#baseball/search/{encoded_name}"
    elif "fanatics" in book_name.lower():
        return f"https://co.fanatics.com/sportsbook/sports/baseball/mlb?search={encoded_name}"
    else:
        return f"https://www.google.com/search?q={encoded_name}+{book_name}+sportsbook"

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page with Bloomberg Terminal styling"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in USERS and check_password_hash(USERS[username], password):
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid credentials'
            return render_template_string(get_login_html(error))

    return render_template_string(get_login_html())

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.pop('user', None)
    return redirect(url_for('login'))

def get_login_html(error=None):
    """Bloomberg Terminal styled login page"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>BLOOMBERG TERMINAL | AUTHENTICATION</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_bloomberg_css()}
        <style>
            .login-container {{
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}

            .login-box {{
                background: #000000;
                border: 3px solid #ff8c00;
                padding: 40px;
                max-width: 500px;
                width: 100%;
                box-shadow: 0 0 20px rgba(255, 140, 0, 0.3);
            }}

            .login-header {{
                text-align: center;
                margin-bottom: 30px;
                border-bottom: 2px solid #ff8c00;
                padding-bottom: 15px;
            }}

            .login-title {{
                color: #ff8c00;
                font-size: 24px;
                font-weight: 700;
                letter-spacing: 2px;
                margin-bottom: 5px;
            }}

            .login-subtitle {{
                color: #ffaa33;
                font-size: 12px;
                letter-spacing: 1px;
            }}

            .form-group {{
                margin-bottom: 20px;
            }}

            .form-label {{
                display: block;
                color: #ff8c00;
                font-size: 12px;
                font-weight: 700;
                margin-bottom: 8px;
                letter-spacing: 1px;
            }}

            .form-input {{
                width: 100%;
                background: #1a1a1a;
                border: 2px solid #ff8c00;
                color: #ffffff;
                padding: 12px;
                font-family: 'Roboto Mono', monospace;
                font-size: 14px;
                outline: none;
                transition: all 0.3s;
            }}

            .form-input:focus {{
                background: #2a2a2a;
                border-color: #ffaa33;
                box-shadow: 0 0 10px rgba(255, 140, 0, 0.3);
            }}

            .login-button {{
                width: 100%;
                background: #ff8c00;
                color: #000000;
                border: none;
                padding: 15px;
                font-family: 'Roboto Mono', monospace;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 2px;
                cursor: pointer;
                transition: all 0.3s;
            }}

            .login-button:hover {{
                background: #ffaa33;
                box-shadow: 0 0 20px rgba(255, 140, 0, 0.5);
            }}

            .error-message {{
                background: #ff0000;
                color: #ffffff;
                padding: 12px;
                margin-bottom: 20px;
                text-align: center;
                font-size: 12px;
                letter-spacing: 1px;
                border: 2px solid #ff4444;
            }}
        </style>
    </head>
    <body>
        <div class="login-container">
            <div class="login-box">
                <div class="login-header">
                    <div class="login-title">BLOOMBERG TERMINAL</div>
                    <div class="login-subtitle">AUTHENTICATION REQUIRED</div>
                </div>

                {'<div class="error-message">⚠ ' + error + '</div>' if error else ''}

                <form method="POST">
                    <div class="form-group">
                        <label class="form-label">USERNAME</label>
                        <input type="text" name="username" class="form-input" required autofocus>
                    </div>

                    <div class="form-group">
                        <label class="form-label">PASSWORD</label>
                        <input type="password" name="password" class="form-input" required>
                    </div>

                    <button type="submit" class="login-button">ACCESS TERMINAL</button>
                </form>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/')
@login_required
def dashboard():
    """Main dashboard route - Overview Stats Only"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()
        
        # Get overall system stats with safe error handling
        stats = {
            'ev_total': 0,
            'ev_positive': 0,
            'splash_total': 0,
            'splash_positive': 0,
            'total_players': 0,
            'total_books': 0
        }
        
        try:
            cursor.execute("SELECT COUNT(*) as total FROM ev_opportunities")
            result = cursor.fetchone()
            stats['ev_total'] = safe_int(result['total'] if result else 0)
        except Exception as e:
            print(f"Error getting ev_total: {e}")
        
        try:
            cursor.execute("SELECT COUNT(*) as total FROM ev_opportunities WHERE ev_percentage > 0")
            result = cursor.fetchone()
            stats['ev_positive'] = safe_int(result['total'] if result else 0)
        except Exception as e:
            print(f"Error getting ev_positive: {e}")
        
        try:
            cursor.execute("SELECT COUNT(*) as total FROM splash_ev_analysis")
            result = cursor.fetchone()
            stats['splash_total'] = safe_int(result['total'] if result else 0)
        except Exception as e:
            print(f"Error getting splash_total: {e}")
        
        try:
            cursor.execute("SELECT COUNT(*) as total FROM splash_ev_analysis WHERE profitable = 1")
            result = cursor.fetchone()
            stats['splash_positive'] = safe_int(result['total'] if result else 0)
        except Exception as e:
            print(f"Error getting splash_positive: {e}")
        
        try:
            cursor.execute("SELECT COUNT(DISTINCT Player) as total FROM player_props")
            result = cursor.fetchone()
            stats['total_players'] = safe_int(result['total'] if result else 0)
        except Exception as e:
            print(f"Error getting total_players: {e}")
        
        try:
            cursor.execute("SELECT COUNT(DISTINCT book) as total FROM player_props")
            result = cursor.fetchone()
            stats['total_books'] = safe_int(result['total'] if result else 0)
        except Exception as e:
            print(f"Error getting total_books: {e}")
        
        conn.close()
        
        # Build HTML with safe stats
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | EV BETTING SYSTEM</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {get_bloomberg_css()}
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">EV BETTING SYSTEM v2.0</div>
                    <div class="terminal-nav">
                        <a href="/" class="nav-btn active">HOME</a>
                        <a href="/ev-opportunities" class="nav-btn">EV OPS</a>
                        <a href="/raw-odds" class="nav-btn">ODDS</a>
                        <a href="/splash-ev" class="nav-btn">SPLASH</a>
                        <button onclick="updateData()" class="nav-btn update-btn" id="updateBtn">UPDATE</button>
                    </div>
                </div>
                
                <div class="terminal-content">
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-value">{stats['ev_total']}</div>
                            <div class="stat-label">SPORTSBOOK OPPORTUNITIES</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{stats['ev_positive']}</div>
                            <div class="stat-label">POSITIVE EV BETS</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{stats['splash_total']}</div>
                            <div class="stat-label">SPLASH PROPS ANALYZED</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{stats['splash_positive']}</div>
                            <div class="stat-label">PROFITABLE SPLASH BETS</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{stats['total_players']}</div>
                            <div class="stat-label">UNIQUE PLAYERS</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{stats['total_books']}</div>
                            <div class="stat-label">SPORTSBOOKS TRACKED</div>
                        </div>
                    </div>
                    
                    <div class="progress-container" id="progressContainer">
                        <div class="progress-bar">
                            <div class="progress-fill" id="progressFill"></div>
                        </div>
                        <div class="progress-text" id="progressText">UPDATING SYSTEM...</div>
                    </div>
                    
                    <div class="info-panel">
                        <strong>SYSTEM STATUS:</strong> OPERATIONAL | 
                        <strong>DATA SOURCES:</strong> SPLASH SPORTS + {stats['total_books']} SPORTSBOOKS | 
                        <strong>LAST UPDATE:</strong> REAL-TIME | 
                        <strong>LEAGUES:</strong> MLB + WNBA
                    </div>
                    
                    <div class="info-panel">
                        <strong>NAVIGATION:</strong><br>
                        • <strong>EV OPS:</strong> Individual sportsbook betting opportunities<br>
                        • <strong>ODDS:</strong> Raw odds comparison across all sportsbooks<br>
                        • <strong>SPLASH:</strong> Contest strategy and parlay optimization<br>
                        • <strong>UPDATE:</strong> Refresh all data sources
                    </div>
                </div>
            </div>
            
            <script>
                let updateInProgress = false;
                
                async function updateData() {{
                    if (updateInProgress) return;
                    
                    updateInProgress = true;
                    const btn = document.getElementById('updateBtn');
                    const progressContainer = document.getElementById('progressContainer');
                    const progressFill = document.getElementById('progressFill');
                    const progressText = document.getElementById('progressText');
                    
                    btn.disabled = true;
                    btn.textContent = 'UPDATING...';
                    progressContainer.style.display = 'block';
                    
                    try {{
                        // Step 1: Splash Sports
                        progressFill.style.width = '10%';
                        progressText.textContent = 'COLLECTING SPLASH DATA...';
                        
                        const splashResponse = await fetch('/api/run-splash', {{method: 'POST'}});
                        const splashResult = await splashResponse.json();
                        
                        if (!splashResult.success) {{
                            throw new Error(splashResult.message);
                        }}
                        
                        progressFill.style.width = '30%';
                        progressText.textContent = 'COLLECTING SPORTSBOOK ODDS...';
                        
                        // Step 2: Odds API
                        const oddsResponse = await fetch('/api/run-odds', {{method: 'POST'}});
                        const oddsResult = await oddsResponse.json();
                        
                        if (!oddsResult.success) {{
                            throw new Error(oddsResult.message);
                        }}
                        
                        // Display API usage
                        if (oddsResult.tokens_used) {{
                            progressText.textContent = `SPORTSBOOK ODDS COLLECTED - API TOKENS USED: ${{oddsResult.tokens_used}}`;
                        }}
                        
                        progressFill.style.width = '60%';
                        progressText.textContent = 'GENERATING EV REPORTS...';
                        
                        // Step 3: Create Report
                        const reportResponse = await fetch('/api/run-report', {{method: 'POST'}});
                        const reportResult = await reportResponse.json();
                        
                        if (!reportResult.success) {{
                            throw new Error(reportResult.message);
                        }}
                        
                        progressFill.style.width = '80%';
                        progressText.textContent = 'CALCULATING SPLASH EV...';
                        
                        // Step 4: Splash EV Analysis
                        const splashEvResponse = await fetch('/api/run-splash-ev', {{method: 'POST'}});
                        const splashEvResult = await splashEvResponse.json();
                        
                        if (!splashEvResult.success) {{
                            throw new Error(splashEvResult.message);
                        }}
                        
                        progressFill.style.width = '90%';
                        progressText.textContent = 'GENERATING PARLAY COMBINATIONS...';
                        
                        // Step 5: Parlay Report
                        const parlayResponse = await fetch('/api/run-parlay-report', {{method: 'POST'}});
                        const parlayResult = await parlayResponse.json();
                        
                        if (!parlayResult.success) {{
                            throw new Error(parlayResult.message);
                        }}
                        
                        progressFill.style.width = '100%';
                        
                        // Calculate total tokens used
                        const totalTokens = (oddsResult.tokens_used || 0);
                        progressText.textContent = `UPDATE COMPLETE - TOTAL API TOKENS: ${{totalTokens}} - REFRESHING...`;
                        
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 2000);
                        
                    }} catch (error) {{
                        progressFill.style.width = '0%';
                        progressText.textContent = `ERROR: ${{error.message}}`;
                        progressText.style.color = '#ff6666';
                        console.error('Update failed:', error);
                        
                        // Show error details in console for debugging
                        if (error.detail) {{
                            console.error('Error details:', error.detail);
                        }}
                    }} finally {{
                        setTimeout(() => {{
                            btn.disabled = false;
                            btn.textContent = 'UPDATE';
                            updateInProgress = false;
                            progressContainer.style.display = 'none';
                        }}, 3000);
                    }}
                }}
            </script>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | ERROR</title>
            {get_bloomberg_css()}
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">SYSTEM ERROR</div>
                </div>
                <div class="terminal-content">
                    <div class="info-panel">
                        <strong>ERROR:</strong> {str(e)}<br>
                        <pre style="color: #ff6666; font-size: 9px; margin-top: 10px;">{error_detail}</pre>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''

@app.route('/ev-opportunities')
@login_required
def ev_opportunities():
    """EV Opportunities page - Bloomberg Terminal Style with Tabs"""
    try:
        # Get view parameter (singles or parlays)
        view = request.args.get('view', default='singles', type=str)

        if view == 'parlays':
            # Get sport parameter for parlays (mlb, nfl, ncaaf)
            sport = request.args.get('sport', default='mlb', type=str)

            if sport == 'nfl':
                return ev_parlays_nfl_view()
            elif sport == 'ncaaf':
                return ev_parlays_ncaaf_view()
            else:  # Default to MLB
                return ev_parlays_view()
        else:
            return ev_singles_view()

    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>"

def ev_singles_view():
    """Singles view - EV opportunities from player_props with de-vigged calculations"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()

        # Get filter parameters
        min_ev = request.args.get('min_ev', default=-5, type=float)
        min_book_count = request.args.get('min_book_count', default=1, type=int)

        # Splash implied probability for EV calculation
        SPLASH_IMPLIED_PROB = Decimal(1/3)**(Decimal(1/2))

        # Get all unique props from player_props
        cursor.execute("""
            SELECT DISTINCT
                Player,
                market,
                line,
                ou,
                home,
                away,
                league
            FROM player_props
            WHERE ou IN ('O', 'U')
            GROUP BY Player, market, line, ou, home, away, league
        """)
        all_props = cursor.fetchall()

        # Calculate EV for each prop
        report_data = []

        for prop in all_props:
            # Get all books with this prop (both sides)
            cursor.execute("""
                SELECT book, ou, dxodds
                FROM player_props
                WHERE Player = %s
                AND market = %s
                AND line = %s
                AND home = %s
                AND away = %s
                AND dxodds IS NOT NULL
            """, (prop['Player'], prop['market'], prop['line'], prop['home'], prop['away']))

            odds_data = cursor.fetchall()
            if not odds_data:
                continue

            # Group by book to find books with both sides
            book_odds = {}
            for row in odds_data:
                book = row['book']
                if book not in book_odds:
                    book_odds[book] = {}
                book_odds[book][row['ou']] = row['dxodds']

            # Calculate de-vigged probabilities for books with both sides
            valid_probs = []
            for book, odds in book_odds.items():
                if 'O' in odds and 'U' in odds:
                    over_odds = Decimal(str(odds['O']))
                    under_odds = Decimal(str(odds['U']))

                    # Convert to probability
                    if over_odds < 0:
                        over_prob = abs(over_odds) / (abs(over_odds) + 100)
                    else:
                        over_prob = 100 / (over_odds + 100)

                    if under_odds < 0:
                        under_prob = abs(under_odds) / (abs(under_odds) + 100)
                    else:
                        under_prob = 100 / (under_odds + 100)

                    # De-vig
                    total = over_prob + under_prob
                    true_over = over_prob / total
                    true_under = under_prob / total

                    valid_probs.append({'O': true_over, 'U': true_under})

            if not valid_probs:
                continue

            # Average de-vigged probability for the requested side
            avg_prob = sum(p[prop['ou']] for p in valid_probs) / len(valid_probs)

            # Calculate EV vs Splash
            ev_percent = float((avg_prob - SPLASH_IMPLIED_PROB) * 100)

            # Filter by min_ev and min_book_count
            book_count = len(valid_probs)
            if ev_percent >= min_ev and book_count >= min_book_count:
                report_data.append({
                    'player_name': prop['Player'],
                    'market_type': prop['market'],
                    'ou': prop['ou'],
                    'line': prop['line'],
                    'ev_percentage': ev_percent,
                    'book_count': book_count,
                    'home_team': prop['home'],
                    'away_team': prop['away'],
                    'league': prop['league']
                })

        # Sort by EV descending
        report_data.sort(key=lambda x: x['ev_percentage'], reverse=True)
        
        conn.close()
        
        # Get summary stats
        total_opportunities = len(report_data)
        positive_ev_count = len([r for r in report_data if safe_float(r.get('ev_percentage', 0)) > 0])
        
        # Safe average calculation
        if report_data:
            avg_ev = sum([safe_float(r.get('ev_percentage', 0)) for r in report_data]) / len(report_data)
            max_ev = max([safe_float(r.get('ev_percentage', 0)) for r in report_data])
        else:
            avg_ev = 0
            max_ev = 0
        
        # Build HTML
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | EV OPPORTUNITIES</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {get_bloomberg_css()}
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">SPORTSBOOK EV OPPORTUNITIES</div>
                    <div class="terminal-nav">
                        <a href="/" class="nav-btn">HOME</a>
                        <a href="/ev-opportunities" class="nav-btn active">EV OPS</a>
                        <a href="/raw-odds" class="nav-btn">ODDS</a>
                        <button onclick="updateData()" class="nav-btn update-btn">UPDATE</button>
                    </div>
                </div>
                
                <div class="terminal-content">
                    <div class="tab-container">
                        <button class="tab-btn active" onclick="window.location.href='/ev-opportunities?view=singles'">SINGLES</button>
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=parlays'">PARLAYS</button>
                    </div>
                    
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-value">{total_opportunities}</div>
                            <div class="stat-label">TOTAL OPPORTUNITIES</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{positive_ev_count}</div>
                            <div class="stat-label">POSITIVE EV</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{avg_ev:.2f}%</div>
                            <div class="stat-label">AVERAGE EV</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{max_ev:.2f}%</div>
                            <div class="stat-label">MAXIMUM EV</div>
                        </div>
                    </div>
                    
                    <div class="info-panel">
                        <strong>SPORTSBOOK BETTING:</strong> Individual prop bets with calculated expected value vs market consensus
                    </div>
                    
                    <div class="controls">
                        <input type="text" id="searchInput" class="search-input" placeholder="SEARCH PLAYERS..." onkeyup="filterTable()">
                        <div class="filter-group">
                            <span class="filter-label">MIN EV%:</span>
                            <input type="number" id="minEvFilter" class="filter-input" value="{min_ev}" step="0.1">
                        </div>
                        <div class="filter-group">
                            <span class="filter-label">MIN BOOKS:</span>
                            <input type="number" id="minBooksFilter" class="filter-input" value="{min_book_count}" min="1" max="10">
                        </div>
                        <button class="apply-filters-btn" onclick="applyEVFilters()">APPLY</button>
                        <div class="pagination">
                            <button class="page-btn" onclick="previousPage()" id="prevBtn">PREV</button>
                            <span class="page-info" id="pageInfo">Page 1</span>
                            <button class="page-btn" onclick="nextPage()" id="nextBtn">NEXT</button>
                        </div>
                    </div>
                    
                    <table class="data-table" id="dataTable">
                        <thead>
                            <tr>
                                <th>PLAYER</th>
                                <th>LGE</th>
                                <th>MARKET</th>
                                <th>SIDE</th>
                                <th>LINE</th>
                                <th>EV%</th>
                                <th>BOOKS</th>
                                <th>MATCHUP</th>
                            </tr>
                        </thead>
                        <tbody>
        '''
        
        for row in report_data:
            # Safe extraction of all values
            player_name = str(row.get('player_name', 'Unknown'))
            market_type = str(row.get('market_type', 'Unknown'))
            ou = str(row.get('ou', 'O'))
            line = safe_float(row.get('line', 0))
            ev = safe_float(row.get('ev_percentage', 0))
            book_count = safe_int(row.get('book_count', 0))
            home_team = str(row.get('home_team', ''))
            away_team = str(row.get('away_team', ''))
            league = str(row.get('league', 'N/A'))
            
            # Determine EV class
            if ev >= 5:
                ev_class = "ev-prime"
            elif ev >= 2:
                ev_class = "ev-good"
            elif ev >= 0:
                ev_class = "ev-marginal"
            else:
                ev_class = "ev-negative"
            
            # League class
            if league and league != 'N/A':
                league_class = f"league-{league.lower()}"
                league_display = league.upper()
            else:
                league_class = ""
                league_display = 'N/A'
            
            # Side class and display
            if ou.upper() == 'O':
                side_class = "side-over"
                side_display = 'O'
            else:
                side_class = "side-under"
                side_display = 'U'
            
            matchup = f"{away_team} @ {home_team}" if away_team and home_team else "N/A"
            
            html += f'''
                <tr class="{ev_class}">
                    <td class="player-name">{player_name}</td>
                    <td class="{league_class}">{league_display}</td>
                    <td>{market_type}</td>
                    <td class="{side_class}">{side_display}</td>
                    <td>{line}</td>
                    <td style="font-weight: 700;">{'+'if ev >= 0 else ''}{ev:.2f}</td>
                    <td>{book_count}</td>
                    <td style="font-size: 9px;">{matchup}</td>
                </tr>
            '''
        
        html += '''
                        </tbody>
                    </table>
                </div>
            </div>
            
            <script>
                async function updateData() {{
                    // Run the update directly instead of redirecting
                    const btn = document.querySelector('.update-btn');
                    btn.disabled = true;
                    btn.textContent = 'UPDATING...';
                    
                    try {{
                        // Run all scripts
                        await fetch('/api/run-splash', {{method: 'POST'}});
                        await fetch('/api/run-odds', {{method: 'POST'}});
                        await fetch('/api/run-report', {{method: 'POST'}});
                        await fetch('/api/run-parlay-report', {{method: 'POST'}});
                        await fetch('/api/run-splash-ev', {{method: 'POST'}});
                        
                        // Reload the page to show updated data
                        window.location.reload();
                    }} catch (error) {{
                        alert('Update failed: ' + error.message);
                        btn.disabled = false;
                        btn.textContent = 'UPDATE';
                    }}
                }}
                
                var currentPage = 1;
                var rowsPerPage = 50;
                var allRows = [];
                var filteredRows = [];
                
                function initPagination() {
                    const table = document.getElementById('dataTable');
                    const tbody = table.getElementsByTagName('tbody')[0];
                    allRows = Array.from(tbody.getElementsByTagName('tr'));
                    filteredRows = allRows.slice();
                    showPage(1);
                }
                
                function showPage(page) {
                    currentPage = page;
                    const start = (page - 1) * rowsPerPage;
                    const end = start + rowsPerPage;
                    
                    // Hide all rows
                    allRows.forEach(row => row.style.display = 'none');
                    
                    // Show rows for current page
                    filteredRows.slice(start, end).forEach(row => row.style.display = '');
                    
                    // Update pagination controls
                    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
                    document.getElementById('pageInfo').textContent = `Page ${page} of ${totalPages}`;
                    document.getElementById('prevBtn').disabled = page === 1;
                    document.getElementById('nextBtn').disabled = page === totalPages || totalPages === 0;
                }
                
                function filterTable() {
                    const input = document.getElementById('searchInput');
                    const filter = input.value.toLowerCase();
                    
                    if (filter === '') {
                        filteredRows = allRows.slice();
                    } else {
                        filteredRows = allRows.filter(row => {
                            const playerCell = row.getElementsByTagName('td')[0];
                            if (playerCell) {
                                const playerName = playerCell.textContent || playerCell.innerText;
                                return playerName.toLowerCase().includes(filter);
                            }
                            return false;
                        });
                    }
                    
                    showPage(1);
                }
                
                function previousPage() {
                    if (currentPage > 1) {
                        showPage(currentPage - 1);
                    }
                }
                
                function nextPage() {
                    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
                    if (currentPage < totalPages) {
                        showPage(currentPage + 1);
                    }
                }
                
                // Raw odds specific filter function
                if (typeof filterTableOdds === 'undefined') {
                    window.filterTableOdds = function() {
                        const searchFilter = document.getElementById('searchInput').value.toLowerCase();
                        const marketFilter = document.getElementById('marketFilter') ? document.getElementById('marketFilter').value : '';
                        const leagueFilter = document.getElementById('leagueFilter') ? document.getElementById('leagueFilter').value : '';
                        
                        filteredRows = allRows.filter(row => {
                            const cells = row.getElementsByTagName('td');
                            if (cells.length < 3) return false;
                            
                            const playerName = cells[0].textContent || cells[0].innerText;
                            const league = cells[1].textContent || cells[1].innerText;
                            const market = cells[2].textContent || cells[2].innerText;
                            
                            let passesSearch = !searchFilter || playerName.toLowerCase().includes(searchFilter);
                            let passesMarket = !marketFilter || market.includes(marketFilter);
                            let passesLeague = !leagueFilter || league === leagueFilter;
                            
                            return passesSearch && passesMarket && passesLeague;
                        });
                        
                        showPage(1);
                    };
                }
                
                // Initialize pagination when page loads
                window.addEventListener('DOMContentLoaded', initPagination);
            </script>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | ERROR</title>
            {get_bloomberg_css()}
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">SYSTEM ERROR</div>
                </div>
                <div class="terminal-content">
                    <div class="info-panel">
                        <strong>ERROR:</strong> {str(e)}<br>
                        <pre style="color: #ff6666; font-size: 9px; margin-top: 10px;">{error_detail}</pre>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''

def ev_parlays_view():
    """Parlays view - shows 3 specific pitcher correlation stacks"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()

        # Splash implied probability for EV calculation
        SPLASH_IMPLIED_PROB = Decimal(1/3)**(Decimal(1/2))

        # Function to calculate de-vigged probability and EV
        def calculate_prop_ev(player_name, market, line, ou, home, away):
            """Calculate EV for a prop using de-vigged probabilities"""
            # Get all books with this prop (both sides)
            cursor.execute("""
                SELECT book, ou, dxodds
                FROM player_props
                WHERE Player = %s
                AND market = %s
                AND line = %s
                AND home = %s
                AND away = %s
                AND dxodds IS NOT NULL
            """, (player_name, market, line, home, away))

            odds_data = cursor.fetchall()
            if not odds_data:
                return None

            # Group by book to find books with both sides
            book_odds = {}
            for row in odds_data:
                book = row['book']
                if book not in book_odds:
                    book_odds[book] = {}
                book_odds[book][row['ou']] = row['dxodds']

            # Calculate de-vigged probabilities for books with both sides
            valid_probs = []
            for book, odds in book_odds.items():
                if 'O' in odds and 'U' in odds:
                    over_odds = Decimal(str(odds['O']))
                    under_odds = Decimal(str(odds['U']))

                    # Convert to probability
                    if over_odds < 0:
                        over_prob = abs(over_odds) / (abs(over_odds) + 100)
                    else:
                        over_prob = 100 / (over_odds + 100)

                    if under_odds < 0:
                        under_prob = abs(under_odds) / (abs(under_odds) + 100)
                    else:
                        under_prob = 100 / (under_odds + 100)

                    # De-vig
                    total = over_prob + under_prob
                    true_over = over_prob / total
                    true_under = under_prob / total

                    valid_probs.append({'O': true_over, 'U': true_under})

            if not valid_probs:
                return None

            # Average de-vigged probability
            avg_prob = sum(p[ou] for p in valid_probs) / len(valid_probs)

            # Calculate EV vs Splash
            ev_percent = float((avg_prob - SPLASH_IMPLIED_PROB) * 100)

            return ev_percent

        # Function to get correlation data for each stack
        def get_correlation_stack(pitcher_market, batter_market, correlation_name):
            """Get pitcher-batter correlations for a specific market pair using player_props"""

            # Get unique pitchers with de-vigged probabilities
            # Join with splash_props to get team info
            pitcher_query = """
                SELECT DISTINCT
                    pp.Player as pitcher_name,
                    pp.market as pitcher_market,
                    pp.line as pitcher_line,
                    pp.ou as pitcher_ou,
                    pp.home,
                    pp.away,
                    sp.team_abbr as pitcher_team
                FROM player_props pp
                JOIN splash_props sp ON (
                    pp.normalized_name = sp.normalized_name
                    AND pp.line = sp.line
                    AND pp.market = CASE sp.market
                        WHEN 'pitcher_ks' THEN 'pitcher_strikeouts'
                        WHEN 'strikeouts' THEN 'pitcher_strikeouts'
                        WHEN 'earned_runs' THEN 'pitcher_earned_runs'
                        WHEN 'allowed_hits' THEN 'pitcher_hits_allowed'
                        WHEN 'hits_allowed' THEN 'pitcher_hits_allowed'
                        WHEN 'outs' THEN 'pitcher_outs'
                        WHEN 'total_outs' THEN 'pitcher_outs'
                        ELSE sp.market
                    END
                )
                WHERE pp.market = %s
                AND pp.league = 'MLB'
                GROUP BY pp.Player, pp.market, pp.line, pp.ou, pp.home, pp.away, sp.team_abbr
            """

            cursor.execute(pitcher_query, (pitcher_market,))
            pitchers = cursor.fetchall()

            correlations = []
            for pitcher in pitchers:
                # Calculate pitcher EV
                pitcher_ev = calculate_prop_ev(
                    pitcher['pitcher_name'],
                    pitcher['pitcher_market'],
                    pitcher['pitcher_line'],
                    pitcher['pitcher_ou'],
                    pitcher['home'],
                    pitcher['away']
                )

                if pitcher_ev is None:
                    continue

                pitcher_dict = {
                    'pitcher_name': pitcher['pitcher_name'],
                    'pitcher_market': pitcher['pitcher_market'],
                    'pitcher_line': float(pitcher['pitcher_line']),
                    'pitcher_ou': pitcher['pitcher_ou'],
                    'pitcher_ev': pitcher_ev,
                    'home_team': pitcher['home'],
                    'away_team': pitcher['away'],
                    'pitcher_team': pitcher['pitcher_team'],
                    'batters': []
                }

                # Get batters from OPPOSING team with SAME over/under
                # If pitcher is home team, get away batters. If pitcher is away, get home batters.
                batter_query = """
                    SELECT DISTINCT
                        pp.Player as batter_name,
                        pp.market as batter_market,
                        pp.line as batter_line,
                        pp.ou as batter_ou,
                        sp.team_abbr as batter_team
                    FROM player_props pp
                    JOIN splash_props sp ON (
                        pp.normalized_name = sp.normalized_name
                        AND pp.line = sp.line
                        AND pp.market = CASE sp.market
                            WHEN 'hits' THEN 'batter_hits'
                            WHEN 'singles' THEN 'batter_singles'
                            WHEN 'runs' THEN 'batter_runs_scored'
                            WHEN 'rbis' THEN 'batter_rbis'
                            WHEN 'total_bases' THEN 'batter_total_bases'
                            WHEN 'hits_allowed' THEN 'pitcher_hits_allowed'
                            WHEN 'allowed_hits' THEN 'pitcher_hits_allowed'
                            WHEN 'earned_runs' THEN 'pitcher_earned_runs'
                            WHEN 'pitcher_ks' THEN 'pitcher_strikeouts'
                            WHEN 'strikeouts' THEN 'pitcher_strikeouts'
                            ELSE sp.market
                        END
                    )
                    WHERE pp.market = %s
                    AND pp.league = 'MLB'
                    AND pp.home = %s
                    AND pp.away = %s
                    AND pp.ou = %s
                    AND pp.Player != %s
                    AND sp.team_abbr != %s
                    GROUP BY pp.Player, pp.market, pp.line, pp.ou, sp.team_abbr
                """

                cursor.execute(batter_query, (
                    batter_market,
                    pitcher['home'],
                    pitcher['away'],
                    pitcher['pitcher_ou'],
                    pitcher['pitcher_name'],
                    pitcher['pitcher_team']
                ))
                batters = cursor.fetchall()

                for batter in batters:
                    # Calculate batter EV
                    batter_ev = calculate_prop_ev(
                        batter['batter_name'],
                        batter['batter_market'],
                        batter['batter_line'],
                        batter['batter_ou'],
                        pitcher['home'],
                        pitcher['away']
                    )

                    if batter_ev is None:
                        continue

                    pitcher_dict['batters'].append({
                        'player_name': batter['batter_name'],
                        'market': batter['batter_market'],
                        'line': float(batter['batter_line']),
                        'ou': batter['batter_ou'],
                        'ev': batter_ev
                    })

                if pitcher_dict['batters']:  # Only add if there are correlated batters
                    correlations.append(pitcher_dict)

            # Sort by pitcher EV descending
            correlations.sort(key=lambda x: x['pitcher_ev'], reverse=True)
            return correlations

        # Get all three correlation stacks with correct market names
        stack1_data = get_correlation_stack('pitcher_earned_runs', 'batter_runs_scored', 'Earned Runs + Batter Runs')
        stack2_data = get_correlation_stack('pitcher_hits_allowed', 'batter_hits', 'Allowed Hits + Batter Hits')
        stack3_data = get_correlation_stack('pitcher_hits_allowed', 'batter_singles', 'Allowed Hits + Batter Singles')

        conn.close()

        # Build HTML with 3-column layout
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | CORRELATION PARLAYS</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {get_bloomberg_css()}
            <style>
                .parlays-container {{
                    display: flex;
                    gap: 10px;
                    margin: 10px;
                }}

                .correlation-tile {{
                    flex: 1;
                    min-width: 0;
                    border: 2px solid #ff8c00;
                    background: #000000;
                }}

                .tile-header {{
                    background: #1a1a1a;
                    padding: 10px;
                    border-bottom: 2px solid #ff8c00;
                    text-align: center;
                    font-weight: 700;
                    color: #ffaa33;
                    font-size: 14px;
                }}

                .parlay-item {{
                    border-bottom: 1px solid #333;
                    padding: 10px;
                }}

                .pitcher-info {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                    padding: 5px;
                    background: #1a1a1a;
                }}

                .pitcher-name {{
                    font-weight: 700;
                    color: #ffaa33;
                    font-size: 13px;
                }}

                .pitcher-prop {{
                    color: #ff8c00;
                    font-size: 11px;
                }}

                .pitcher-ev {{
                    font-weight: 700;
                    font-size: 13px;
                }}

                .batter-info {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 3px 5px;
                    margin: 2px 0;
                    background: #0a0a0a;
                    cursor: pointer;
                    transition: all 0.2s;
                }}

                .batter-info:hover {{
                    background: #1a1a1a;
                    padding-left: 10px;
                }}

                .batter-name {{
                    color: #ffffff;
                    font-size: 11px;
                }}

                .batter-prop {{
                    color: #cc7000;
                    font-size: 10px;
                }}

                .batter-ev {{
                    font-weight: 700;
                    font-size: 11px;
                }}

                .ev-positive {{
                    color: #90ee90;
                }}

                .ev-negative {{
                    color: #ff6666;
                }}

                .game-info {{
                    font-size: 10px;
                    color: #888;
                    margin-top: 5px;
                    text-align: center;
                }}

                .no-data {{
                    text-align: center;
                    padding: 20px;
                    color: #ff8c00;
                    font-size: 12px;
                }}

                @media (max-width: 768px) {{
                    .parlays-container {{
                        flex-direction: column;
                    }}
                    .correlation-tile {{
                        width: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">PITCHER CORRELATION STACKS</div>
                    <div class="terminal-nav">
                        <a href="/" class="nav-btn">HOME</a>
                        <a href="/ev-opportunities" class="nav-btn active">EV OPS</a>
                        <a href="/raw-odds" class="nav-btn">ODDS</a>
                        <button onclick="updateData()" class="nav-btn update-btn">UPDATE MLB</button>
                    </div>
                </div>

                <div class="terminal-content">
                    <div class="tab-container">
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=singles'">SINGLES</button>
                        <button class="tab-btn active" onclick="window.location.href='/ev-opportunities?view=parlays'">PARLAYS</button>
                    </div>

                    <!-- Sport sub-tabs for Parlays -->
                    <div class="tab-container" style="margin-top: 10px; border-top: 1px solid #333;">
                        <button class="tab-btn active" onclick="window.location.href='/ev-opportunities?view=parlays&sport=mlb'">MLB</button>
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=parlays&sport=nfl'">NFL</button>
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=parlays&sport=ncaaf'">NCAAF</button>
                    </div>

                    <div class="info-panel">
                        <strong>MLB CORRELATION PARLAYS:</strong> Three specific pitcher-batter correlations. Sorted by highest pitcher EV. All MLB props shown.
                    </div>

                    <div class="parlays-container">
                        <!-- Stack 1: Earned Runs + Batter Runs -->
                        <div class="correlation-tile">
                            <div class="tile-header">EARNED RUNS + BATTER RUNS</div>
                            <div class="tile-content">
        '''

        # Add Stack 1 data
        if stack1_data:
            for parlay in stack1_data:
                ev_class = 'ev-positive' if parlay['pitcher_ev'] >= 0 else 'ev-negative'
                html += f'''
                                <div class="parlay-item">
                                    <div class="pitcher-info">
                                        <div>
                                            <div class="pitcher-name">{parlay['pitcher_name']}</div>
                                            <div class="pitcher-prop">{parlay['pitcher_market'].replace('_', ' ').upper()} {parlay['pitcher_ou']} {parlay['pitcher_line']}</div>
                                        </div>
                                        <div class="pitcher-ev {ev_class}">
                                            {'+'if parlay['pitcher_ev'] >= 0 else ''}{parlay['pitcher_ev']:.1f}%
                                        </div>
                                    </div>
                '''
                for batter in parlay['batters']:
                    batter_ev_class = 'ev-positive' if batter['ev'] >= 0 else 'ev-negative'
                    html += f'''
                                    <div class="batter-info">
                                        <div>
                                            <span class="batter-name">{batter['player_name']}</span>
                                            <span class="batter-prop">{batter['market'].replace('_', ' ')} {batter['ou']} {batter['line']}</span>
                                        </div>
                                        <div class="batter-ev {batter_ev_class}">
                                            {'+'if batter['ev'] >= 0 else ''}{batter['ev']:.1f}%
                                        </div>
                                    </div>
                    '''
                html += f'''
                                    <div class="game-info">{parlay['away_team']} @ {parlay['home_team']}</div>
                                </div>
                '''
        else:
            html += '<div class="no-data">No earned runs correlations available</div>'

        html += '''
                            </div>
                        </div>

                        <!-- Stack 2: Allowed Hits + Batter Hits -->
                        <div class="correlation-tile">
                            <div class="tile-header">ALLOWED HITS + BATTER HITS</div>
                            <div class="tile-content">
        '''

        # Add Stack 2 data
        if stack2_data:
            for parlay in stack2_data:
                ev_class = 'ev-positive' if parlay['pitcher_ev'] >= 0 else 'ev-negative'
                html += f'''
                                <div class="parlay-item">
                                    <div class="pitcher-info">
                                        <div>
                                            <div class="pitcher-name">{parlay['pitcher_name']}</div>
                                            <div class="pitcher-prop">{parlay['pitcher_market'].replace('_', ' ').upper()} {parlay['pitcher_ou']} {parlay['pitcher_line']}</div>
                                        </div>
                                        <div class="pitcher-ev {ev_class}">
                                            {'+'if parlay['pitcher_ev'] >= 0 else ''}{parlay['pitcher_ev']:.1f}%
                                        </div>
                                    </div>
                '''
                for batter in parlay['batters']:
                    batter_ev_class = 'ev-positive' if batter['ev'] >= 0 else 'ev-negative'
                    html += f'''
                                    <div class="batter-info">
                                        <div>
                                            <span class="batter-name">{batter['player_name']}</span>
                                            <span class="batter-prop">{batter['market'].replace('_', ' ')} {batter['ou']} {batter['line']}</span>
                                        </div>
                                        <div class="batter-ev {batter_ev_class}">
                                            {'+'if batter['ev'] >= 0 else ''}{batter['ev']:.1f}%
                                        </div>
                                    </div>
                    '''
                html += f'''
                                    <div class="game-info">{parlay['away_team']} @ {parlay['home_team']}</div>
                                </div>
                '''
        else:
            html += '<div class="no-data">No hits correlations available</div>'

        html += '''
                            </div>
                        </div>

                        <!-- Stack 3: Allowed Hits + Batter Singles -->
                        <div class="correlation-tile">
                            <div class="tile-header">ALLOWED HITS + BATTER SINGLES</div>
                            <div class="tile-content">
        '''

        # Add Stack 3 data
        if stack3_data:
            for parlay in stack3_data:
                ev_class = 'ev-positive' if parlay['pitcher_ev'] >= 0 else 'ev-negative'
                html += f'''
                                <div class="parlay-item">
                                    <div class="pitcher-info">
                                        <div>
                                            <div class="pitcher-name">{parlay['pitcher_name']}</div>
                                            <div class="pitcher-prop">{parlay['pitcher_market'].replace('_', ' ').upper()} {parlay['pitcher_ou']} {parlay['pitcher_line']}</div>
                                        </div>
                                        <div class="pitcher-ev {ev_class}">
                                            {'+'if parlay['pitcher_ev'] >= 0 else ''}{parlay['pitcher_ev']:.1f}%
                                        </div>
                                    </div>
                '''
                for batter in parlay['batters']:
                    batter_ev_class = 'ev-positive' if batter['ev'] >= 0 else 'ev-negative'
                    html += f'''
                                    <div class="batter-info">
                                        <div>
                                            <span class="batter-name">{batter['player_name']}</span>
                                            <span class="batter-prop">{batter['market'].replace('_', ' ')} {batter['ou']} {batter['line']}</span>
                                        </div>
                                        <div class="batter-ev {batter_ev_class}">
                                            {'+'if batter['ev'] >= 0 else ''}{batter['ev']:.1f}%
                                        </div>
                                    </div>
                    '''
                html += f'''
                                    <div class="game-info">{parlay['away_team']} @ {parlay['home_team']}</div>
                                </div>
                '''
        else:
            html += '<div class="no-data">No singles correlations available</div>'

        html += '''
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                async function updateData() {
                    const btn = document.querySelector('.update-btn');
                    btn.disabled = true;
                    btn.textContent = 'UPDATING...';

                    try {
                        // Run MLB-specific scripts
                        await fetch('/api/run-splash', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({sports: ['mlb']})
                        });
                        await fetch('/api/run-odds', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({sports: ['mlb']})
                        });

                        // Reload the page to show updated data
                        window.location.reload();
                    } catch (error) {
                        alert('Update failed: ' + error.message);
                        btn.disabled = false;
                        btn.textContent = 'UPDATE MLB';
                    }
                }
            </script>
        </body>
        </html>
        '''

        return html

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f'''
        <div style="color: red; padding: 20px;">
            <h1>Error loading Parlay Opportunities</h1>
            <p>{str(e)}</p>
            <pre>{error_detail}</pre>
        </div>
        '''

def ev_parlays_nfl_view():
    """NFL Parlays view - shows QB-anchored correlation stacks (Yards and Completions)"""
    try:
        # Fetch NFL correlation stacks directly from API function
        api_response = api_nfl_correlation_stacks()
        data = api_response.get_json()

        if not data.get('success'):
            raise Exception(data.get('message', 'Failed to load NFL correlation stacks'))

        stacks = data.get('stacks', {})
        yards_stacks = stacks.get('yards_stacks', [])
        completions_stacks = stacks.get('completions_stacks', [])

        # Build HTML with 2-column layout
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | NFL CORRELATION PARLAYS</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {get_bloomberg_css()}
            <style>
                .parlays-container {{
                    display: flex;
                    gap: 10px;
                    margin: 10px;
                }}

                .correlation-tile {{
                    flex: 1;
                    min-width: 0;
                    border: 2px solid #ff8c00;
                    background: #000000;
                }}

                .tile-header {{
                    background: #1a1a1a;
                    padding: 10px;
                    border-bottom: 2px solid #ff8c00;
                    text-align: center;
                    font-weight: 700;
                    color: #ffaa33;
                    font-size: 14px;
                }}

                .parlay-item {{
                    border-bottom: 1px solid #333;
                    padding: 10px;
                }}

                .qb-info {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                    padding: 5px;
                    background: #1a1a1a;
                }}

                .qb-name {{
                    font-weight: 700;
                    color: #ffaa33;
                    font-size: 13px;
                }}

                .qb-prop {{
                    color: #ff8c00;
                    font-size: 11px;
                }}

                .qb-ev {{
                    font-weight: 700;
                    font-size: 13px;
                }}

                .receiver-info {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 3px 5px;
                    margin: 2px 0;
                    background: #0a0a0a;
                    cursor: pointer;
                    transition: all 0.2s;
                }}

                .receiver-info:hover {{
                    background: #1a1a1a;
                    padding-left: 10px;
                }}

                .receiver-name {{
                    color: #ffffff;
                    font-size: 11px;
                }}

                .receiver-prop {{
                    color: #cc7000;
                    font-size: 10px;
                }}

                .receiver-position {{
                    color: #888;
                    font-size: 10px;
                    font-weight: 700;
                }}

                .receiver-corr {{
                    color: #6495ED;
                    font-size: 10px;
                    font-weight: 700;
                }}

                .receiver-ev {{
                    font-weight: 700;
                    font-size: 11px;
                }}

                .ev-positive {{
                    color: #90ee90;
                }}

                .ev-negative {{
                    color: #ff6666;
                }}

                .game-info {{
                    font-size: 10px;
                    color: #888;
                    margin-top: 5px;
                    text-align: center;
                }}

                .no-data {{
                    text-align: center;
                    padding: 20px;
                    color: #ff8c00;
                    font-size: 12px;
                }}

                @media (max-width: 768px) {{
                    .parlays-container {{
                        flex-direction: column;
                    }}
                    .correlation-tile {{
                        width: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">NFL QB CORRELATION STACKS</div>
                    <div class="terminal-nav">
                        <a href="/" class="nav-btn">HOME</a>
                        <a href="/ev-opportunities" class="nav-btn active">EV OPS</a>
                        <a href="/raw-odds" class="nav-btn">ODDS</a>
                        <button onclick="updateData()" class="nav-btn update-btn">UPDATE NFL</button>
                    </div>
                </div>

                <div class="terminal-content">
                    <div class="tab-container">
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=singles'">SINGLES</button>
                        <button class="tab-btn active" onclick="window.location.href='/ev-opportunities?view=parlays'">PARLAYS</button>
                    </div>

                    <!-- Sport sub-tabs for Parlays -->
                    <div class="tab-container" style="margin-top: 10px; border-top: 1px solid #333;">
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=parlays&sport=mlb'">MLB</button>
                        <button class="tab-btn active" onclick="window.location.href='/ev-opportunities?view=parlays&sport=nfl'">NFL</button>
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=parlays&sport=ncaaf'">NCAAF</button>
                    </div>

                    <div class="info-panel">
                        <strong>NFL CORRELATION PARLAYS:</strong> QB-anchored stacks with correlated receivers. Sorted by highest QB EV. All NFL props shown.
                    </div>

                    <div class="parlays-container">
                        <!-- Yards Correlation Column -->
                        <div class="correlation-tile">
                            <div class="tile-header">PASS YARDS + RECEIVING YARDS</div>
                            <div class="tile-content">
        '''

        # Add Yards stacks
        if yards_stacks:
            for stack in yards_stacks:
                qb = stack['qb']
                qb_ev_class = 'ev-positive' if qb['ev'] >= 0 else 'ev-negative'
                html += f'''
                                <div class="parlay-item">
                                    <div class="qb-info">
                                        <div>
                                            <div class="qb-name">{qb['player_name']}</div>
                                            <div class="qb-prop">PASS YDS {qb['ou']} {qb['line']:.1f} | Books: {qb['book_count']}</div>
                                        </div>
                                        <div class="qb-ev {qb_ev_class}">
                                            {'+'if qb['ev'] >= 0 else ''}{qb['ev']:.1f}%
                                        </div>
                                    </div>
                '''

                receivers = stack['receivers']
                if receivers:
                    html += '<div style="margin-left: 10px;">'
                    for receiver in receivers:
                        receiver_ev_class = 'ev-positive' if receiver['ev'] >= 0 else 'ev-negative'
                        html += f'''
                                    <div class="receiver-info">
                                        <div>
                                            <span class="receiver-position">{receiver['position']}</span>
                                            <span class="receiver-name">{receiver['player_name']}</span>
                                            <span class="receiver-prop">REC YDS {receiver['ou']} {receiver['line']:.1f}</span>
                                            <span class="receiver-corr">Corr: {receiver['correlation_score']:.2f}</span>
                                        </div>
                                        <div class="receiver-ev {receiver_ev_class}">
                                            {'+'if receiver['ev'] >= 0 else ''}{receiver['ev']:.1f}%
                                        </div>
                                    </div>
                        '''
                    html += '</div>'
                else:
                    html += '<div style="margin-left: 10px; color: #888; font-size: 10px;">No correlated receivers</div>'

                html += f'''
                                    <div class="game-info">{qb['away']} @ {qb['home']}</div>
                                </div>
                '''
        else:
            html += '<div class="no-data">No yards correlations available</div>'

        html += '''
                            </div>
                        </div>

                        <!-- Completions Correlation Column -->
                        <div class="correlation-tile">
                            <div class="tile-header">PASS COMPLETIONS + RECEPTIONS</div>
                            <div class="tile-content">
        '''

        # Add Completions stacks
        if completions_stacks:
            for stack in completions_stacks:
                qb = stack['qb']
                qb_ev_class = 'ev-positive' if qb['ev'] >= 0 else 'ev-negative'
                html += f'''
                                <div class="parlay-item">
                                    <div class="qb-info">
                                        <div>
                                            <div class="qb-name">{qb['player_name']}</div>
                                            <div class="qb-prop">COMPLETIONS {qb['ou']} {qb['line']:.1f} | Books: {qb['book_count']}</div>
                                        </div>
                                        <div class="qb-ev {qb_ev_class}">
                                            {'+'if qb['ev'] >= 0 else ''}{qb['ev']:.1f}%
                                        </div>
                                    </div>
                '''

                receivers = stack['receivers']
                if receivers:
                    html += '<div style="margin-left: 10px;">'
                    for receiver in receivers:
                        receiver_ev_class = 'ev-positive' if receiver['ev'] >= 0 else 'ev-negative'
                        html += f'''
                                    <div class="receiver-info">
                                        <div>
                                            <span class="receiver-position">{receiver['position']}</span>
                                            <span class="receiver-name">{receiver['player_name']}</span>
                                            <span class="receiver-prop">RECEPTIONS {receiver['ou']} {receiver['line']:.1f}</span>
                                            <span class="receiver-corr">Corr: {receiver['correlation_score']:.2f}</span>
                                        </div>
                                        <div class="receiver-ev {receiver_ev_class}">
                                            {'+'if receiver['ev'] >= 0 else ''}{receiver['ev']:.1f}%
                                        </div>
                                    </div>
                        '''
                    html += '</div>'
                else:
                    html += '<div style="margin-left: 10px; color: #888; font-size: 10px;">No correlated receivers</div>'

                html += f'''
                                    <div class="game-info">{qb['away']} @ {qb['home']}</div>
                                </div>
                '''
        else:
            html += '<div class="no-data">No completions correlations available</div>'

        html += '''
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                async function updateData() {
                    const btn = document.querySelector('.update-btn');
                    btn.disabled = true;
                    btn.textContent = 'UPDATING...';

                    try {
                        // Run NFL-specific scripts
                        await fetch('/api/run-splash', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({sports: ['nfl']})
                        });
                        await fetch('/api/run-odds', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({sports: ['nfl']})
                        });

                        // Reload the page to show updated data
                        window.location.reload();
                    } catch (error) {
                        alert('Update failed: ' + error.message);
                        btn.disabled = false;
                        btn.textContent = 'UPDATE NFL';
                    }
                }
            </script>
        </body>
        </html>
        '''

        return html

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f'''
        <div style="color: red; padding: 20px;">
            <h1>Error loading NFL Parlay Opportunities</h1>
            <p>{str(e)}</p>
            <pre>{error_detail}</pre>
        </div>
        '''

def ev_parlays_ncaaf_view():
    """NCAAF Parlays view - shows QB-anchored correlation stacks (Yards and Completions)"""
    try:
        # Fetch NCAAF correlation stacks directly from API function
        api_response = api_ncaaf_correlation_stacks()
        data = api_response.get_json()

        if not data.get('success'):
            raise Exception(data.get('message', 'Failed to load NCAAF correlation stacks'))

        stacks = data.get('stacks', {})
        yards_stacks = stacks.get('yards_stacks', [])
        completions_stacks = stacks.get('completions_stacks', [])

        # Build HTML with 2-column layout
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | NCAAF CORRELATION PARLAYS</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {get_bloomberg_css()}
            <style>
                .parlays-container {{
                    display: flex;
                    gap: 10px;
                    margin: 10px;
                }}

                .correlation-tile {{
                    flex: 1;
                    min-width: 0;
                    border: 2px solid #ff8c00;
                    background: #000000;
                }}

                .tile-header {{
                    background: #1a1a1a;
                    padding: 10px;
                    border-bottom: 2px solid #ff8c00;
                    text-align: center;
                    font-weight: 700;
                    color: #ffaa33;
                    font-size: 14px;
                }}

                .parlay-item {{
                    border-bottom: 1px solid #333;
                    padding: 10px;
                }}

                .qb-info {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                    padding: 5px;
                    background: #1a1a1a;
                }}

                .qb-name {{
                    font-weight: 700;
                    color: #ffaa33;
                    font-size: 13px;
                }}

                .qb-prop {{
                    color: #ff8c00;
                    font-size: 11px;
                }}

                .qb-ev {{
                    font-weight: 700;
                    font-size: 13px;
                }}

                .receiver-info {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 3px 5px;
                    margin: 2px 0;
                    background: #0a0a0a;
                    cursor: pointer;
                    transition: all 0.2s;
                }}

                .receiver-info:hover {{
                    background: #1a1a1a;
                    padding-left: 10px;
                }}

                .receiver-name {{
                    color: #ffffff;
                    font-size: 11px;
                }}

                .receiver-prop {{
                    color: #cc7000;
                    font-size: 10px;
                }}

                .receiver-position {{
                    color: #888;
                    font-size: 10px;
                    font-weight: 700;
                }}

                .receiver-corr {{
                    color: #6495ED;
                    font-size: 10px;
                    font-weight: 700;
                }}

                .receiver-ev {{
                    font-weight: 700;
                    font-size: 11px;
                }}

                .ev-positive {{
                    color: #90ee90;
                }}

                .ev-negative {{
                    color: #ff6666;
                }}

                .game-info {{
                    font-size: 10px;
                    color: #888;
                    margin-top: 5px;
                    text-align: center;
                }}

                .no-data {{
                    text-align: center;
                    padding: 20px;
                    color: #ff8c00;
                    font-size: 12px;
                }}

                @media (max-width: 768px) {{
                    .parlays-container {{
                        flex-direction: column;
                    }}
                    .correlation-tile {{
                        width: 100%;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">NCAAF QB CORRELATION STACKS</div>
                    <div class="terminal-nav">
                        <a href="/" class="nav-btn">HOME</a>
                        <a href="/ev-opportunities" class="nav-btn active">EV OPS</a>
                        <a href="/raw-odds" class="nav-btn">ODDS</a>
                        <button onclick="updateData()" class="nav-btn update-btn">UPDATE NCAAF</button>
                    </div>
                </div>

                <div class="terminal-content">
                    <div class="tab-container">
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=singles'">SINGLES</button>
                        <button class="tab-btn active" onclick="window.location.href='/ev-opportunities?view=parlays'">PARLAYS</button>
                    </div>

                    <!-- Sport sub-tabs for Parlays -->
                    <div class="tab-container" style="margin-top: 10px; border-top: 1px solid #333;">
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=parlays&sport=mlb'">MLB</button>
                        <button class="tab-btn" onclick="window.location.href='/ev-opportunities?view=parlays&sport=nfl'">NFL</button>
                        <button class="tab-btn active" onclick="window.location.href='/ev-opportunities?view=parlays&sport=ncaaf'">NCAAF</button>
                    </div>

                    <div class="info-panel">
                        <strong>NCAAF CORRELATION PARLAYS:</strong> QB-anchored stacks with correlated receivers. Sorted by highest QB EV. All NCAAF props shown.
                    </div>

                    <div class="parlays-container">
                        <!-- Yards Correlation Column -->
                        <div class="correlation-tile">
                            <div class="tile-header">PASS YARDS + RECEIVING YARDS</div>
                            <div class="tile-content">
        '''

        # Add Yards stacks
        if yards_stacks:
            for stack in yards_stacks:
                qb = stack['qb']
                qb_ev_class = 'ev-positive' if qb['ev'] >= 0 else 'ev-negative'
                html += f'''
                                <div class="parlay-item">
                                    <div class="qb-info">
                                        <div>
                                            <div class="qb-name">{qb['player_name']}</div>
                                            <div class="qb-prop">PASS YDS {qb['ou']} {qb['line']:.1f} | Books: {qb['book_count']}</div>
                                        </div>
                                        <div class="qb-ev {qb_ev_class}">
                                            {'+'if qb['ev'] >= 0 else ''}{qb['ev']:.1f}%
                                        </div>
                                    </div>
                '''

                receivers = stack['receivers']
                if receivers:
                    html += '<div style="margin-left: 10px;">'
                    for receiver in receivers:
                        receiver_ev_class = 'ev-positive' if receiver['ev'] >= 0 else 'ev-negative'
                        html += f'''
                                    <div class="receiver-info">
                                        <div>
                                            <span class="receiver-position">{receiver['position']}</span>
                                            <span class="receiver-name">{receiver['player_name']}</span>
                                            <span class="receiver-prop">REC YDS {receiver['ou']} {receiver['line']:.1f}</span>
                                            <span class="receiver-corr">Corr: {receiver['correlation_score']:.2f}</span>
                                        </div>
                                        <div class="receiver-ev {receiver_ev_class}">
                                            {'+'if receiver['ev'] >= 0 else ''}{receiver['ev']:.1f}%
                                        </div>
                                    </div>
                        '''
                    html += '</div>'
                else:
                    html += '<div style="margin-left: 10px; color: #888; font-size: 10px;">No correlated receivers</div>'

                html += f'''
                                    <div class="game-info">{qb['away']} @ {qb['home']}</div>
                                </div>
                '''
        else:
            html += '<div class="no-data">No yards correlations available</div>'

        html += '''
                            </div>
                        </div>

                        <!-- Completions Correlation Column -->
                        <div class="correlation-tile">
                            <div class="tile-header">PASS COMPLETIONS + RECEPTIONS</div>
                            <div class="tile-content">
        '''

        # Add Completions stacks
        if completions_stacks:
            for stack in completions_stacks:
                qb = stack['qb']
                qb_ev_class = 'ev-positive' if qb['ev'] >= 0 else 'ev-negative'
                html += f'''
                                <div class="parlay-item">
                                    <div class="qb-info">
                                        <div>
                                            <div class="qb-name">{qb['player_name']}</div>
                                            <div class="qb-prop">COMPLETIONS {qb['ou']} {qb['line']:.1f} | Books: {qb['book_count']}</div>
                                        </div>
                                        <div class="qb-ev {qb_ev_class}">
                                            {'+'if qb['ev'] >= 0 else ''}{qb['ev']:.1f}%
                                        </div>
                                    </div>
                '''

                receivers = stack['receivers']
                if receivers:
                    html += '<div style="margin-left: 10px;">'
                    for receiver in receivers:
                        receiver_ev_class = 'ev-positive' if receiver['ev'] >= 0 else 'ev-negative'
                        html += f'''
                                    <div class="receiver-info">
                                        <div>
                                            <span class="receiver-position">{receiver['position']}</span>
                                            <span class="receiver-name">{receiver['player_name']}</span>
                                            <span class="receiver-prop">RECEPTIONS {receiver['ou']} {receiver['line']:.1f}</span>
                                            <span class="receiver-corr">Corr: {receiver['correlation_score']:.2f}</span>
                                        </div>
                                        <div class="receiver-ev {receiver_ev_class}">
                                            {'+'if receiver['ev'] >= 0 else ''}{receiver['ev']:.1f}%
                                        </div>
                                    </div>
                        '''
                    html += '</div>'
                else:
                    html += '<div style="margin-left: 10px; color: #888; font-size: 10px;">No correlated receivers</div>'

                html += f'''
                                    <div class="game-info">{qb['away']} @ {qb['home']}</div>
                                </div>
                '''
        else:
            html += '<div class="no-data">No completions correlations available</div>'

        html += '''
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <script>
                async function updateData() {
                    const btn = document.querySelector('.update-btn');
                    btn.disabled = true;
                    btn.textContent = 'UPDATING...';

                    try {
                        // Run NCAAF-specific scripts
                        await fetch('/api/run-splash', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({sports: ['ncaaf']})
                        });
                        await fetch('/api/run-odds', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({sports: ['ncaaf']})
                        });

                        // Reload the page to show updated data
                        window.location.reload();
                    } catch (error) {
                        alert('Update failed: ' + error.message);
                        btn.disabled = false;
                        btn.textContent = 'UPDATE NCAAF';
                    }
                }
            </script>
        </body>
        </html>
        '''

        return html

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f'''
        <div style="color: red; padding: 20px;">
            <h1>Error loading NCAAF Parlay Opportunities</h1>
            <p>{str(e)}</p>
            <pre>{error_detail}</pre>
        </div>
        '''

@app.route('/splash-ev')
@login_required
def splash_ev():
    """Splash EV Opportunities - Bloomberg Terminal Style"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()
        
        # Get filter parameters
        min_ev = request.args.get('min_ev', default=-5, type=float)  # Show negative EVs too
        profitable_only = request.args.get('profitable_only', default='false')  # Show all props by default
        
        # Get Splash EV opportunities - Check if league column exists first
        cursor.execute("SHOW COLUMNS FROM splash_ev_analysis LIKE 'league'")
        has_league_column = cursor.fetchone() is not None
        
        if profitable_only == 'true':
            if has_league_column:
                cursor.execute("""
                    SELECT player_name, market as market_type, side, line, league, ev_percentage,
                           true_probability, public_appeal_score, book_count,
                           adjusted_breakeven, profitable
                    FROM splash_ev_analysis
                    WHERE profitable = 1 AND ev_percentage >= %s
                    ORDER BY ev_percentage DESC
                """, (min_ev,))
            else:
                cursor.execute("""
                    SELECT player_name, market as market_type, side, line, 'N/A' as league, ev_percentage,
                           true_probability, public_appeal_score, book_count,
                           adjusted_breakeven, profitable
                    FROM splash_ev_analysis
                    WHERE profitable = 1 AND ev_percentage >= %s
                    ORDER BY ev_percentage DESC
                """, (min_ev,))
        else:
            if has_league_column:
                cursor.execute("""
                    SELECT player_name, market as market_type, side, line, league, ev_percentage,
                           true_probability, public_appeal_score, book_count,
                           adjusted_breakeven, profitable
                    FROM splash_ev_analysis
                    WHERE ev_percentage >= %s
                    ORDER BY ev_percentage DESC
                """, (min_ev,))
            else:
                cursor.execute("""
                    SELECT player_name, market as market_type, side, line, 'N/A' as league, ev_percentage,
                           true_probability, public_appeal_score, book_count,
                           adjusted_breakeven, profitable
                    FROM splash_ev_analysis
                    WHERE ev_percentage >= %s
                    ORDER BY ev_percentage DESC
                """, (min_ev,))
        
        splash_data = cursor.fetchall()
        
        # Get summary stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_props,
                COUNT(CASE WHEN profitable = 1 THEN 1 END) as profitable_props,
                AVG(ev_percentage) as avg_ev,
                MAX(ev_percentage) as max_ev
            FROM splash_ev_analysis
        """)
        summary = cursor.fetchone()
        
        conn.close()
        
        # Build HTML
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | SPLASH EV ANALYSIS</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {get_bloomberg_css()}
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">SPLASH CONTEST STRATEGY</div>
                    <div class="terminal-nav">
                        <a href="/" class="nav-btn">HOME</a>
                        <a href="/ev-opportunities" class="nav-btn">EV OPS</a>
                        <a href="/raw-odds" class="nav-btn">ODDS</a>
                        <a href="/splash-ev" class="nav-btn active">SPLASH</a>
                        <button onclick="updateData()" class="nav-btn update-btn">UPDATE</button>
                    </div>
                </div>
                
                <div class="terminal-content">
                    <div class="stats-grid">
                        <div class="stat-box">
                            <div class="stat-value">{safe_int(summary.get('total_props', 0))}</div>
                            <div class="stat-label">TOTAL ANALYZED</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{safe_int(summary.get('profitable_props', 0))}</div>
                            <div class="stat-label">PROFITABLE</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{safe_float(summary.get('avg_ev', 0)):.2f}%</div>
                            <div class="stat-label">AVG EV</div>
                        </div>
                        <div class="stat-box">
                            <div class="stat-value">{safe_float(summary.get('max_ev', 0)):.2f}%</div>
                            <div class="stat-label">MAX EV</div>
                        </div>
                    </div>
                    
                    <div class="controls">
                        <input type="text" id="searchInput" class="search-input" placeholder="SEARCH PLAYERS..." onkeyup="filterTable()">
                        <button class="filter-btn active" onclick="filterProfitable('all')" id="filterAll">ALL</button>
                        <button class="filter-btn" onclick="filterProfitable('positive')" id="filterPositive">+EV ONLY</button>
                        <button class="filter-btn" onclick="filterProfitable('negative')" id="filterNegative">-EV ONLY</button>
                        <div class="filter-group">
                            <span class="filter-label">MIN EV%:</span>
                            <input type="number" id="minEvFilterSplash" class="filter-input" value="{min_ev}" step="0.1">
                        </div>
                        <button class="apply-filters-btn" onclick="applySplashFilters()">APPLY</button>
                        <div class="pagination">
                            <button class="page-btn" onclick="previousPage()" id="prevBtn">PREV</button>
                            <span class="page-info" id="pageInfo">Page 1</span>
                            <button class="page-btn" onclick="nextPage()" id="nextBtn">NEXT</button>
                        </div>
                    </div>
                    
                    <div class="info-panel">
                        <strong>SPLASH STRATEGY:</strong> 
                        <strong style="color: #90ee90;">PRIME</strong> (5%+ EV) | 
                        <strong style="color: #98d982;">GOOD</strong> (2-5% EV) | 
                        <strong style="color: #ff8c00;">MARGINAL</strong> (0-2% EV) | 
                        <strong>APPEAL:</strong> <span style="color: #90ee90;">LOW</span> = LESS PUBLIC ATTENTION
                    </div>
                    
                    <table class="data-table" id="dataTable">
                        <thead>
                            <tr>
                                <th>PLAYER</th>
                                <th>LGE</th>
                                <th>MARKET</th>
                                <th>SIDE</th>
                                <th>LINE</th>
                                <th>EV%</th>
                                <th>PROB</th>
                                <th>APPEAL</th>
                                <th>BOOKS</th>
                                <th>STRATEGY</th>
                            </tr>
                        </thead>
                        <tbody>
        '''
        
        for row in splash_data:
            # Safe value extraction
            player_name = str(row.get('player_name', 'Unknown'))
            market_type = str(row.get('market_type', 'Unknown'))
            side = str(row.get('side', 'O'))
            line = safe_float(row.get('line', 0))
            league = str(row.get('league', 'N/A'))
            ev = safe_float(row.get('ev_percentage', 0))
            prob = safe_float(row.get('true_probability', 0))
            appeal = safe_int(row.get('public_appeal_score', 0))
            book_count = safe_int(row.get('book_count', 0))
            
            if ev >= 5:
                strategy = "PRIME"
                strategy_class = "strategy-prime"
                row_class = "ev-prime"
            elif ev >= 2:
                strategy = "GOOD"
                strategy_class = "strategy-good"
                row_class = "ev-good"
            elif ev >= 0:
                strategy = "MARGINAL"
                strategy_class = "strategy-marginal"
                row_class = "ev-marginal"
            else:
                strategy = "AVOID"
                strategy_class = "strategy-avoid"
                row_class = "ev-negative"
            
            # Appeal score styling
            if appeal <= 1:
                appeal_class = "appeal-low"
            elif appeal <= 3:
                appeal_class = "appeal-medium"
            else:
                appeal_class = "appeal-high"
            
            # League class
            league_class = f"league-{league.lower()}" if league != 'N/A' else ""
            league_display = league.upper() if league != 'N/A' else 'N/A'
            
            # Side class
            side_class = "side-over" if side.upper() == 'O' else "side-under"
            
            html += f'''
                <tr class="{row_class}">
                    <td class="player-name">{player_name}</td>
                    <td class="{league_class}">{league_display}</td>
                    <td>{market_type}</td>
                    <td class="{side_class}">{side}</td>
                    <td>{line}</td>
                    <td style="font-weight: 700;">{'+'if ev >= 0 else ''}{ev:.2f}</td>
                    <td>{prob:.1f}%</td>
                    <td class="{appeal_class}">{appeal}</td>
                    <td>{book_count}</td>
                    <td class="{strategy_class}">{strategy}</td>
                </tr>
            '''
        
        html += '''
                        </tbody>
                    </table>
                </div>
            </div>
            
            <script>
                var currentPage = 1;
                var rowsPerPage = 50;
                var allRows = [];
                var filteredRows = [];
                var currentFilter = 'all';
                
                function initPagination() {
                    const table = document.getElementById('dataTable');
                    const tbody = table.getElementsByTagName('tbody')[0];
                    allRows = Array.from(tbody.getElementsByTagName('tr'));
                    filteredRows = allRows.slice();
                    showPage(1);
                }
                
                function showPage(page) {
                    currentPage = page;
                    const start = (page - 1) * rowsPerPage;
                    const end = start + rowsPerPage;
                    
                    // Hide all rows
                    allRows.forEach(row => row.style.display = 'none');
                    
                    // Show rows for current page
                    filteredRows.slice(start, end).forEach(row => row.style.display = '');
                    
                    // Update pagination controls
                    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
                    document.getElementById('pageInfo').textContent = `Page ${page} of ${totalPages}`;
                    document.getElementById('prevBtn').disabled = page === 1;
                    document.getElementById('nextBtn').disabled = page === totalPages || totalPages === 0;
                }
                
                function applyFilters() {
                    const searchFilter = document.getElementById('searchInput').value.toLowerCase();
                    
                    filteredRows = allRows.filter(row => {
                        const playerCell = row.getElementsByTagName('td')[0];
                        const evCell = row.getElementsByTagName('td')[5];
                        
                        // Search filter
                        let passesSearch = true;
                        if (searchFilter && playerCell) {
                            const playerName = playerCell.textContent || playerCell.innerText;
                            passesSearch = playerName.toLowerCase().includes(searchFilter);
                        }
                        
                        // Profitability filter
                        let passesProfitability = true;
                        if (currentFilter !== 'all' && evCell) {
                            const ev = parseFloat(evCell.textContent.replace('%', ''));
                            if (currentFilter === 'positive') passesProfitability = ev >= 0;
                            else if (currentFilter === 'negative') passesProfitability = ev < 0;
                        }
                        
                        return passesSearch && passesProfitability;
                    });
                    
                    showPage(1);
                }
                
                function filterTable() {
                    applyFilters();
                }
                
                function filterProfitable(type) {
                    currentFilter = type;
                    
                    // Update button states
                    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                    document.getElementById('filter' + type.charAt(0).toUpperCase() + type.slice(1)).classList.add('active');
                    
                    applyFilters();
                }
                
                function previousPage() {
                    if (currentPage > 1) {
                        showPage(currentPage - 1);
                    }
                }
                
                function nextPage() {
                    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
                    if (currentPage < totalPages) {
                        showPage(currentPage + 1);
                    }
                }
                
                function applyEVFilters() {
                    const minEv = document.getElementById('minEvFilter').value;
                    const minBooks = document.getElementById('minBooksFilter').value;
                    window.location.href = `/ev-opportunities?min_ev=${minEv}&min_book_count=${minBooks}`;
                }
                
                // Raw odds specific filter function
                if (typeof filterTableOdds === 'undefined') {
                    window.filterTableOdds = function() {
                        const searchFilter = document.getElementById('searchInput').value.toLowerCase();
                        const marketFilter = document.getElementById('marketFilter') ? document.getElementById('marketFilter').value : '';
                        const leagueFilter = document.getElementById('leagueFilter') ? document.getElementById('leagueFilter').value : '';
                        
                        filteredRows = allRows.filter(row => {
                            const cells = row.getElementsByTagName('td');
                            if (cells.length < 3) return false;
                            
                            const playerName = cells[0].textContent || cells[0].innerText;
                            const league = cells[1].textContent || cells[1].innerText;
                            const market = cells[2].textContent || cells[2].innerText;
                            
                            let passesSearch = !searchFilter || playerName.toLowerCase().includes(searchFilter);
                            let passesMarket = !marketFilter || market.includes(marketFilter);
                            let passesLeague = !leagueFilter || league === leagueFilter;
                            
                            return passesSearch && passesMarket && passesLeague;
                        });
                        
                        showPage(1);
                    };
                }
                
                function applySplashFilters() {
                    const minEv = document.getElementById('minEvFilterSplash').value;
                    const profitableOnly = currentFilter === 'positive' ? 'true' : 'false';
                    window.location.href = `/splash-ev?min_ev=${minEv}&profitable_only=${profitableOnly}`;
                }
                
                // Initialize pagination when page loads
                window.addEventListener('DOMContentLoaded', initPagination);
                
                async function updateData() {{
                    // Run the update directly instead of redirecting
                    const btn = document.querySelector('.update-btn');
                    btn.disabled = true;
                    btn.textContent = 'UPDATING...';
                    
                    try {{
                        // Run all scripts
                        await fetch('/api/run-splash', {{method: 'POST'}});
                        await fetch('/api/run-odds', {{method: 'POST'}});
                        await fetch('/api/run-report', {{method: 'POST'}});
                        await fetch('/api/run-parlay-report', {{method: 'POST'}});
                        await fetch('/api/run-splash-ev', {{method: 'POST'}});
                        
                        // Reload the page to show updated data
                        window.location.reload();
                    }} catch (error) {{
                        alert('Update failed: ' + error.message);
                        btn.disabled = false;
                        btn.textContent = 'UPDATE';
                    }}
                }}
            </script>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | ERROR</title>
            {get_bloomberg_css()}
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">SYSTEM ERROR</div>
                </div>
                <div class="terminal-content">
                    <div class="info-panel">
                        <strong>ERROR:</strong> {str(e)}<br>
                        <pre style="color: #ff6666; font-size: 9px; margin-top: 10px;">{error_detail}</pre>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''

@app.route('/raw-odds')
@login_required
def raw_odds():
    """Raw odds comparison page with individual sportsbook columns and clickable links"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()
        
        # Get filter parameters
        min_ev = request.args.get('min_ev', default=0, type=float)
        
        # Get recent props to display - get PAIRS of props (both sides)
        try:
            cursor.execute("""
                SELECT Player as player_name, market as market_type, line, 
                       MAX(league) as league
                FROM player_props 
                WHERE refreshed >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY Player, market, line
                ORDER BY refreshed DESC
            """)
            
            prop_pairs = cursor.fetchall()
        except Exception as e:
            print(f"Error getting recent props: {e}")
            prop_pairs = []
        
        if not prop_pairs:
            # Fallback to any props if no recent ones
            try:
                cursor.execute("""
                    SELECT Player as player_name, market as market_type, line,
                           MAX(league) as league
                    FROM player_props 
                    GROUP BY Player, market, line
                    ORDER BY Player, market, line
                """)
                prop_pairs = cursor.fetchall()
            except Exception as e:
                print(f"Error getting fallback props: {e}")
                prop_pairs = []
        
        # Build the raw odds data
        raw_data = []
        
        for prop_pair in prop_pairs:
            # Process both Over and Under for each prop
            for side in ['O', 'U']:
                # Get odds for this specific prop and side from all books
                cursor.execute("""
                    SELECT book, dxodds, ou
                    FROM player_props 
                    WHERE Player = %s AND market = %s AND line = %s AND ou = %s
                """, (prop_pair['player_name'], prop_pair['market_type'], prop_pair['line'], side))
                
                side_odds_data = cursor.fetchall()
                
                # Skip if no odds for this side
                if not side_odds_data:
                    continue
                
                # Get ALL odds for both sides to check if prop is one-sided
                cursor.execute("""
                    SELECT book, dxodds, ou
                    FROM player_props 
                    WHERE Player = %s AND market = %s AND line = %s
                """, (prop_pair['player_name'], prop_pair['market_type'], prop_pair['line']))
                
                all_odds_data = cursor.fetchall()
                
                # Check if we have both sides
                has_over = any(odd['ou'] == 'O' for odd in all_odds_data)
                has_under = any(odd['ou'] == 'U' for odd in all_odds_data)
                is_one_sided = not (has_over and has_under)
                
                # Create a row with individual book columns
                row = {
                    'player_name': str(prop_pair.get('player_name', 'Unknown')),
                    'league': str(prop_pair.get('league', 'MLB')),
                    'market_type': str(prop_pair.get('market_type', 'Unknown')), 
                    'line': safe_float(prop_pair.get('line', 0)),
                    'ou': side,
                    'is_one_sided': is_one_sided,
                    'DraftKings': None,
                    'FanDuel': None,
                    'BetMGM': None,
                    'Caesars': None,
                    'BetRivers': None,
                    'Fanatics': None,
                    'ESPN BET': None,
                    'PointsBet': None
                }
                
                # Collect all odds for EV calculation
                all_odds = []
                
                # Fill in the odds for each book
                for odd in side_odds_data:
                    book_name = str(odd.get('book', ''))
                    odds_value = odd.get('dxodds')
                    
                    if odds_value is not None:
                        all_odds.append(odds_value)
                    
                    # Map actual book names to display columns
                    if 'draftkings' in book_name.lower():
                        row['DraftKings'] = odds_value
                    elif 'fanduel' in book_name.lower():
                        row['FanDuel'] = odds_value
                    elif 'betmgm' in book_name.lower():
                        row['BetMGM'] = odds_value
                    elif 'caesars' in book_name.lower():
                        row['Caesars'] = odds_value
                    elif 'betrivers' in book_name.lower():
                        row['BetRivers'] = odds_value
                    elif 'fanatics' in book_name.lower():
                        row['Fanatics'] = odds_value
                    elif 'espn' in book_name.lower():
                        row['ESPN BET'] = odds_value
                    elif 'pointsbet' in book_name.lower():
                        row['PointsBet'] = odds_value
                
                # Calculate EV - use de-vigged if not one-sided
                if is_one_sided:
                    # Use simple average for one-sided props (less accurate)
                    ev = calculate_ev_from_odds(all_odds)
                    row['ev_percentage'] = ev
                    row['ev_note'] = 'One-sided (less accurate)'
                else:
                    # Collect data for de-vigging
                    books_data = [(odd['book'], odd['dxodds'], odd['ou']) for odd in all_odds_data]
                    devigged_evs, has_both = calculate_devigged_ev(books_data)
                    
                    if has_both and devigged_evs:
                        row['ev_percentage'] = devigged_evs[side]
                        row['ev_note'] = 'De-vigged'
                    else:
                        # Fallback to simple average
                        ev = calculate_ev_from_odds(all_odds)
                        row['ev_percentage'] = ev
                        row['ev_note'] = 'No matching pairs'
                
                row['book_count'] = len(all_odds)
                
                raw_data.append(row)
        
        # Sort by EV% descending (highest EV first)
        raw_data.sort(key=lambda x: x.get('ev_percentage') if x.get('ev_percentage') is not None else -999, reverse=True)
        
        conn.close()
        
        # Build HTML with individual sportsbook columns
        html = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | RAW ODDS COMPARISON</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            {get_bloomberg_css()}
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">SPORTSBOOK ODDS COMPARISON</div>
                    <div class="terminal-nav">
                        <a href="/" class="nav-btn">HOME</a>
                        <a href="/ev-opportunities" class="nav-btn">EV OPS</a>
                        <a href="/raw-odds" class="nav-btn active">ODDS</a>
                        <a href="/splash-ev" class="nav-btn">SPLASH</a>
                        <button onclick="updateData()" class="nav-btn update-btn">UPDATE</button>
                    </div>
                </div>
                
                <div class="terminal-content">
                    <div class="info-panel">
                        <strong>RAW ODDS DATA:</strong> Individual sportsbook columns with clickable links | 
                        <strong>CLICK ODDS:</strong> Opens sportsbook for betting |
                        <strong>YELLOW ROWS:</strong> One-sided props (missing Over or Under) - EV less accurate
                    </div>
                    
                    <div class="controls">
                        <input type="text" id="searchInput" class="search-input" placeholder="SEARCH PLAYERS..." onkeyup="filterTableOdds()">
                        <div class="filter-group">
                            <span class="filter-label">MARKET:</span>
                            <select id="marketFilter" class="filter-input" style="width: 150px" onchange="filterTableOdds()">
                                <option value="">ALL MARKETS</option>
                                <option value="pitcher_strikeouts">Pitcher Strikeouts</option>
                                <option value="pitcher_earned_runs">Earned Runs</option>
                                <option value="pitcher_hits_allowed">Hits Allowed</option>
                                <option value="batter_total_bases">Total Bases</option>
                                <option value="batter_hits">Hits</option>
                                <option value="batter_singles">Singles</option>
                                <option value="batter_runs_scored">Runs</option>
                                <option value="batter_rbis">RBIs</option>
                                <option value="pitcher_outs">Outs</option>
                                <option value="player_points">Points</option>
                                <option value="player_rebounds">Rebounds</option>
                                <option value="player_points_rebounds_assists">Pts+Reb+Asts</option>
                            </select>
                        </div>
                        <div class="filter-group">
                            <span class="filter-label">LEAGUE:</span>
                            <select id="leagueFilter" class="filter-input" onchange="filterTableOdds()">
                                <option value="">ALL</option>
                                <option value="MLB">MLB</option>
                                <option value="WNBA">WNBA</option>
                            </select>
                        </div>
                        <div class="pagination">
                            <button class="page-btn" onclick="previousPage()" id="prevBtn">PREV</button>
                            <span class="page-info" id="pageInfo">Page 1</span>
                            <button class="page-btn" onclick="nextPage()" id="nextBtn">NEXT</button>
                        </div>
                    </div>
                    
                    <table class="data-table" id="dataTable">
                        <thead>
                            <tr>
                                <th>PLAYER</th>
                                <th>LGE</th>
                                <th>MARKET</th>
                                <th>EV%</th>
                                <th>LINE</th>
                                <th>SIDE</th>
                                <th>DRAFTKINGS</th>
                                <th>FANDUEL</th>
                                <th>BETMGM</th>
                                <th>CAESARS</th>
                                <th>BETRIVERS</th>
                                <th>FANATICS</th>
                                <th>ESPN</th>
                                <th>POINTSBET</th>
                            </tr>
                        </thead>
                        <tbody>
        '''
        
        for row in raw_data:
            player_name = row['player_name']
            league = row.get('league', 'MLB')
            market_type = row['market_type']
            line = row['line']
            ou = row['ou']
            
            # Side class
            if ou.upper() == 'O':
                side_class = "side-over"
                side_display = 'O'
            else:
                side_class = "side-under"  
                side_display = 'U'
            
            # Create clickable odds for each sportsbook
            def format_odds_cell(book_name, odds_value, player_name, market_type):
                if odds_value is None or odds_value == '':
                    return "-"
                
                try:
                    odds_num = safe_float(odds_value)
                    # Determine odds color
                    odds_class = "odds-positive" if odds_num > 0 else "odds-negative"
                    
                    # Create clickable link
                    url = build_sportsbook_url(book_name, player_name, market_type)
                    return f'<a href="{url}" target="_blank" class="odds-link {odds_class}" title="Bet {player_name} {market_type} {side_display} {line} at {book_name}">{"+" if odds_num > 0 else ""}{odds_num:.0f}</a>'
                except (ValueError, TypeError):
                    return "-"
            
            # Format EV cell
            ev = row.get('ev_percentage')
            if ev is not None:
                ev_class = "positive-ev" if ev >= 0 else "negative-ev"
                ev_display = f'{ev:+.2f}%'
            else:
                ev_class = ""
                ev_display = "-"
            
            # Check if this is a one-sided prop
            row_class = "one-sided-prop" if row.get('is_one_sided', False) else ""
            
            html += f'''
                <tr class="{row_class}">
                    <td class="player-name">{player_name}</td>
                    <td class="league-col">{league}</td>
                    <td>{market_type}</td>
                    <td class="{ev_class}" style="font-weight: 700;" title="{row.get('ev_note', '')}">{ev_display}</td>
                    <td>{line}</td>
                    <td class="{side_class}">{side_display}</td>
                    <td>{format_odds_cell('DraftKings', row.get('DraftKings'), player_name, market_type)}</td>
                    <td>{format_odds_cell('FanDuel', row.get('FanDuel'), player_name, market_type)}</td>
                    <td>{format_odds_cell('BetMGM', row.get('BetMGM'), player_name, market_type)}</td>
                    <td>{format_odds_cell('Caesars', row.get('Caesars'), player_name, market_type)}</td>
                    <td>{format_odds_cell('BetRivers', row.get('BetRivers'), player_name, market_type)}</td>
                    <td>{format_odds_cell('Fanatics', row.get('Fanatics'), player_name, market_type)}</td>
                    <td>{format_odds_cell('ESPN BET', row.get('ESPN BET'), player_name, market_type)}</td>
                    <td>{format_odds_cell('PointsBet', row.get('PointsBet'), player_name, market_type)}</td>
                </tr>
            '''
        
        html += '''
                        </tbody>
                    </table>
                </div>
            </div>
            
            <script>
                async function updateData() {{
                    // Run the update directly instead of redirecting
                    const btn = document.querySelector('.update-btn');
                    btn.disabled = true;
                    btn.textContent = 'UPDATING...';
                    
                    try {{
                        // Run all scripts
                        await fetch('/api/run-splash', {{method: 'POST'}});
                        await fetch('/api/run-odds', {{method: 'POST'}});
                        await fetch('/api/run-report', {{method: 'POST'}});
                        await fetch('/api/run-parlay-report', {{method: 'POST'}});
                        await fetch('/api/run-splash-ev', {{method: 'POST'}});
                        
                        // Reload the page to show updated data
                        window.location.reload();
                    }} catch (error) {{
                        alert('Update failed: ' + error.message);
                        btn.disabled = false;
                        btn.textContent = 'UPDATE';
                    }}
                }}
                
                var currentPage = 1;
                var rowsPerPage = 50;
                var allRows = [];
                var filteredRows = [];
                
                function initPagination() {
                    const table = document.getElementById('dataTable');
                    const tbody = table.getElementsByTagName('tbody')[0];
                    allRows = Array.from(tbody.getElementsByTagName('tr'));
                    filteredRows = allRows.slice();
                    showPage(1);
                }
                
                function showPage(page) {
                    currentPage = page;
                    const start = (page - 1) * rowsPerPage;
                    const end = start + rowsPerPage;
                    
                    // Hide all rows
                    allRows.forEach(row => row.style.display = 'none');
                    
                    // Show rows for current page
                    filteredRows.slice(start, end).forEach(row => row.style.display = '');
                    
                    // Update pagination controls
                    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
                    document.getElementById('pageInfo').textContent = `Page ${page} of ${totalPages}`;
                    document.getElementById('prevBtn').disabled = page === 1;
                    document.getElementById('nextBtn').disabled = page === totalPages || totalPages === 0;
                }
                
                function filterTable() {
                    const input = document.getElementById('searchInput');
                    const filter = input.value.toLowerCase();
                    
                    if (filter === '') {
                        filteredRows = allRows.slice();
                    } else {
                        filteredRows = allRows.filter(row => {
                            const playerCell = row.getElementsByTagName('td')[0];
                            if (playerCell) {
                                const playerName = playerCell.textContent || playerCell.innerText;
                                return playerName.toLowerCase().includes(filter);
                            }
                            return false;
                        });
                    }
                    
                    showPage(1);
                }
                
                function previousPage() {
                    if (currentPage > 1) {
                        showPage(currentPage - 1);
                    }
                }
                
                function nextPage() {
                    const totalPages = Math.ceil(filteredRows.length / rowsPerPage);
                    if (currentPage < totalPages) {
                        showPage(currentPage + 1);
                    }
                }
                
                // Raw odds specific filter function
                if (typeof filterTableOdds === 'undefined') {
                    window.filterTableOdds = function() {
                        const searchFilter = document.getElementById('searchInput').value.toLowerCase();
                        const marketFilter = document.getElementById('marketFilter') ? document.getElementById('marketFilter').value : '';
                        const leagueFilter = document.getElementById('leagueFilter') ? document.getElementById('leagueFilter').value : '';
                        
                        filteredRows = allRows.filter(row => {
                            const cells = row.getElementsByTagName('td');
                            if (cells.length < 3) return false;
                            
                            const playerName = cells[0].textContent || cells[0].innerText;
                            const league = cells[1].textContent || cells[1].innerText;
                            const market = cells[2].textContent || cells[2].innerText;
                            
                            let passesSearch = !searchFilter || playerName.toLowerCase().includes(searchFilter);
                            let passesMarket = !marketFilter || market.includes(marketFilter);
                            let passesLeague = !leagueFilter || league === leagueFilter;
                            
                            return passesSearch && passesMarket && passesLeague;
                        });
                        
                        showPage(1);
                    };
                }
                
                // Initialize pagination when page loads
                window.addEventListener('DOMContentLoaded', initPagination);
            </script>
        </body>
        </html>
        '''
        
        return html
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>BLOOMBERG TERMINAL | ERROR</title>
            {get_bloomberg_css()}
        </head>
        <body>
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-title">SYSTEM ERROR</div>
                </div>
                <div class="terminal-content">
                    <div class="info-panel">
                        <strong>ERROR:</strong> {str(e)}<br>
                        <pre style="color: #ff6666; font-size: 9px; margin-top: 10px;">{error_detail}</pre>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''

# API routes for updating data
@app.route('/api/run-splash', methods=['POST'])
@login_required
def api_run_splash():
    """API endpoint to run Splash scraper with optional sport filter"""
    try:
        if run_splash_scraper_script:
            # Get sport filter from request body
            data = request.get_json() or {}
            sports_filter = data.get('sports', None)  # e.g., ['mlb'] or ['nfl', 'ncaaf']

            if sports_filter:
                run_splash_scraper_script(sports_filter=sports_filter)
                sports_str = ', '.join(sports_filter).upper()
                return jsonify({"success": True, "message": f"Splash scraper completed for {sports_str}"})
            else:
                run_splash_scraper_script()
                return jsonify({"success": True, "message": "Splash scraper completed for all sports"})
        else:
            return jsonify({"success": False, "message": "Splash scraper not available"})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Splash scraper error: {str(e)}", "detail": error_detail})

@app.route('/api/run-odds', methods=['POST'])
@login_required
def api_run_odds():
    """API endpoint to run Odds API with optional sport filter"""
    try:
        if run_odds_api_script:
            # Get sport filter from request body
            data = request.get_json() or {}
            sports_filter = data.get('sports', None)  # e.g., ['mlb'] or ['nfl', 'ncaaf']

            result = run_odds_api_script(sports_filter=sports_filter)

            if result and result.get('success'):
                sports_str = ', '.join(sports_filter).upper() if sports_filter else 'all sports'
                return jsonify({
                    "success": True,
                    "message": f"Odds API completed for {sports_str} - {result.get('props_inserted', 0)} props inserted",
                    "api_calls": result.get('api_calls', 0),
                    "tokens_used": result.get('tokens_used', 0),
                    "props_inserted": result.get('props_inserted', 0)
                })
            else:
                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                return jsonify({
                    "success": False,
                    "message": f"Odds API failed: {error_msg}",
                    "api_calls": result.get('api_calls', 0) if result else 0,
                    "tokens_used": result.get('tokens_used', 0) if result else 0
                })
        else:
            return jsonify({"success": False, "message": "Odds API not available"})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Odds API error: {str(e)}", "detail": error_detail})

@app.route('/api/run-report', methods=['POST'])
@login_required
def api_run_report():
    """API endpoint to run report creation"""
    try:
        if run_create_report_script:
            run_create_report_script()
            return jsonify({"success": True, "message": "Report creation completed"})
        else:
            return jsonify({"success": False, "message": "Report creation not available"})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Report creation error: {str(e)}", "detail": error_detail})

@app.route('/api/run-splash-ev', methods=['POST'])
@login_required
def api_run_splash_ev():
    """API endpoint to run Splash EV analysis"""
    try:
        if run_splash_ev_analysis_script:
            run_splash_ev_analysis_script()
            return jsonify({"success": True, "message": "Splash EV analysis completed"})
        else:
            return jsonify({"success": False, "message": "Splash EV analysis not available"})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Splash EV analysis error: {str(e)}", "detail": error_detail})

@app.route('/api/run-parlay-report', methods=['POST'])
@login_required
def api_run_parlay_report():
    """API endpoint to run parlay report generation"""
    try:
        if run_parlay_report_script:
            run_parlay_report_script()
            return jsonify({"success": True, "message": "Parlay report generation completed"})
        else:
            return jsonify({"success": False, "message": "Parlay report generation not available"})
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Parlay report error: {str(e)}", "detail": error_detail})

@app.route('/api/pitcher-anchored-parlays', methods=['GET'])
@login_required
def api_pitcher_anchored_parlays():
    """API endpoint to get pitcher-anchored parlay data"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()
        
        # Get all props with de-vigged probabilities
        query = """
        SELECT DISTINCT
            sp.player_name,
            sp.normalized_name,
            sp.market,
            sp.line,
            pp.ou,
            pp.home,
            pp.away,
            sp.team_abbr as team,
            COUNT(DISTINCT pp.book) as book_count,
            AVG(CASE 
                WHEN pp.dxodds < 0 THEN ABS(pp.dxodds) / (ABS(pp.dxodds) + 100)
                ELSE 100 / (pp.dxodds + 100)
            END) as avg_probability
        FROM splash_props sp
        JOIN player_props pp ON (
            sp.normalized_name = pp.normalized_name
            AND sp.line = pp.line
            AND pp.market = CASE sp.market
                WHEN 'pitcher_ks' THEN 'pitcher_strikeouts'
                WHEN 'strikeouts' THEN 'pitcher_strikeouts'
                WHEN 'earned_runs' THEN 'pitcher_earned_runs'
                WHEN 'allowed_hits' THEN 'pitcher_hits_allowed'
                WHEN 'hits_allowed' THEN 'pitcher_hits_allowed'
                WHEN 'total_bases' THEN 'batter_total_bases'
                WHEN 'hits' THEN 'batter_hits'
                WHEN 'singles' THEN 'batter_singles'
                WHEN 'runs' THEN 'batter_runs_scored'
                WHEN 'rbis' THEN 'batter_rbis'
                WHEN 'outs' THEN 'pitcher_outs'
                WHEN 'total_outs' THEN 'pitcher_outs'
                ELSE sp.market
            END
        )
        WHERE pp.dxodds IS NOT NULL
        GROUP BY sp.player_name, sp.normalized_name, sp.market, sp.line, pp.ou, pp.home, pp.away, sp.team_abbr
        HAVING book_count >= 2
        """
        
        cursor.execute(query)
        all_props = cursor.fetchall()
        conn.close()
        
        # Process props for parlay generation
        props_list = []
        for prop in all_props:
            # Calculate EV
            true_prob = float(prop['avg_probability'])  # Simplified - should use de-vigging
            splash_prob = 0.5774
            ev_percentage = (true_prob - splash_prob) * 100
            
            props_list.append({
                'player_name': prop['player_name'],
                'normalized_name': prop['normalized_name'],
                'market': prop['market'],
                'line': float(prop['line']),
                'ou': prop['ou'],
                'true_probability': true_prob,
                'ev_percentage': ev_percentage,
                'home': prop['home'],
                'away': prop['away'],
                'team': prop['team'],
                'sport': 'mlb'
            })
        
        # Generate pitcher-anchored parlays
        from data_scripts.pitcher_anchored_parlays import PitcherAnchoredParlayGenerator
        generator = PitcherAnchoredParlayGenerator(props_list)
        display_data = generator.generate_anchor_display_data(limit=10)
        
        return jsonify({
            "success": True,
            "anchors": display_data
        })
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}", "detail": error_detail})

@app.route('/api/nfl-correlation-stacks', methods=['GET'])
@login_required
def api_nfl_correlation_stacks():
    """API endpoint to get NFL QB-anchored correlation stacks"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()

        # Get all NFL props with de-vigged probabilities and positions (Splash-driven)
        query = """
        SELECT DISTINCT
            sp.player_name,
            sp.normalized_name,
            CASE sp.market
                WHEN 'passing_yards' THEN 'player_pass_yds'
                WHEN 'completions' THEN 'player_pass_completions'
                WHEN 'receiving_yards' THEN 'player_reception_yds'
                WHEN 'receiving_receptions' THEN 'player_receptions'
                ELSE sp.market
            END as market,
            sp.line,
            pp.ou,
            pp.home,
            pp.away,
            sp.team_abbr as team,
            pp.position_football,
            COUNT(DISTINCT pp.book) as book_count,
            AVG(CASE
                WHEN pp.dxodds < 0 THEN ABS(pp.dxodds) / (ABS(pp.dxodds) + 100)
                ELSE 100 / (pp.dxodds + 100)
            END) as avg_probability
        FROM splash_props sp
        JOIN player_props pp ON (
            sp.normalized_name = pp.normalized_name
            AND ABS(sp.line - pp.line) <= 1.6
            AND pp.market = CASE sp.market
                WHEN 'passing_yards' THEN 'player_pass_yds'
                WHEN 'completions' THEN 'player_pass_completions'
                WHEN 'receiving_yards' THEN 'player_reception_yds'
                WHEN 'receiving_receptions' THEN 'player_receptions'
                ELSE sp.market
            END
        )
        WHERE sp.sport = 'nfl'
        AND pp.sport = 'nfl'
        AND pp.dxodds IS NOT NULL
        GROUP BY sp.player_name, sp.normalized_name, market, sp.line, pp.ou, pp.home, pp.away, sp.team_abbr, pp.position_football
        HAVING book_count >= 1
        """

        cursor.execute(query)
        all_props = cursor.fetchall()
        conn.close()

        # Process props for parlay generation
        props_list = []
        for prop in all_props:
            # Calculate EV
            true_prob = float(prop['avg_probability'])
            splash_prob = 0.5774
            ev_percentage = (true_prob - splash_prob) * 100

            props_list.append({
                'player_name': prop['player_name'],
                'normalized_name': prop['normalized_name'],
                'market': prop['market'],
                'line': float(prop['line']),
                'ou': prop['ou'],
                'true_probability': true_prob,
                'ev_percentage': ev_percentage,
                'home': prop['home'],
                'away': prop['away'],
                'team': prop['team'],
                'sport': 'nfl',
                'position_football': prop['position_football'],
                'book_count': prop['book_count']
            })

        # Generate QB-anchored parlays
        from data_scripts.qb_anchored_parlays import QBAnchoredParlayGenerator
        generator = QBAnchoredParlayGenerator(props_list, sport='nfl')
        display_data = generator.generate_display_data(limit=10)

        return jsonify({
            "success": True,
            "stacks": display_data
        })

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}", "detail": error_detail})

@app.route('/api/ncaaf-correlation-stacks', methods=['GET'])
@login_required
def api_ncaaf_correlation_stacks():
    """API endpoint to get NCAAF QB-anchored correlation stacks"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()

        # Get all NCAAF props with de-vigged probabilities and positions (Splash-driven)
        query = """
        SELECT DISTINCT
            sp.player_name,
            sp.normalized_name,
            CASE sp.market
                WHEN 'passing_yards' THEN 'player_pass_yds'
                WHEN 'completions' THEN 'player_pass_completions'
                WHEN 'receiving_yards' THEN 'player_reception_yds'
                WHEN 'receiving_receptions' THEN 'player_receptions'
                ELSE sp.market
            END as market,
            sp.line,
            pp.ou,
            pp.home,
            pp.away,
            sp.team_abbr as team,
            pp.position_football,
            COUNT(DISTINCT pp.book) as book_count,
            AVG(CASE
                WHEN pp.dxodds < 0 THEN ABS(pp.dxodds) / (ABS(pp.dxodds) + 100)
                ELSE 100 / (pp.dxodds + 100)
            END) as avg_probability
        FROM splash_props sp
        JOIN player_props pp ON (
            sp.normalized_name = pp.normalized_name
            AND ABS(sp.line - pp.line) <= 1.6
            AND pp.market = CASE sp.market
                WHEN 'passing_yards' THEN 'player_pass_yds'
                WHEN 'completions' THEN 'player_pass_completions'
                WHEN 'receiving_yards' THEN 'player_reception_yds'
                WHEN 'receiving_receptions' THEN 'player_receptions'
                ELSE sp.market
            END
        )
        WHERE sp.sport = 'ncaaf'
        AND pp.sport = 'ncaaf'
        AND pp.dxodds IS NOT NULL
        GROUP BY sp.player_name, sp.normalized_name, market, sp.line, pp.ou, pp.home, pp.away, sp.team_abbr, pp.position_football
        HAVING book_count >= 1
        """

        cursor.execute(query)
        all_props = cursor.fetchall()
        conn.close()

        # Process props for parlay generation
        props_list = []
        for prop in all_props:
            # Calculate EV
            true_prob = float(prop['avg_probability'])
            splash_prob = 0.5774
            ev_percentage = (true_prob - splash_prob) * 100

            props_list.append({
                'player_name': prop['player_name'],
                'normalized_name': prop['normalized_name'],
                'market': prop['market'],
                'line': float(prop['line']),
                'ou': prop['ou'],
                'true_probability': true_prob,
                'ev_percentage': ev_percentage,
                'home': prop['home'],
                'away': prop['away'],
                'team': prop['team'],
                'sport': 'ncaaf',
                'position_football': prop['position_football'],
                'book_count': prop['book_count']
            })

        # Generate QB-anchored parlays
        from data_scripts.qb_anchored_parlays import QBAnchoredParlayGenerator
        generator = QBAnchoredParlayGenerator(props_list, sport='ncaaf')
        display_data = generator.generate_display_data(limit=10)

        return jsonify({
            "success": True,
            "stacks": display_data
        })

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}", "detail": error_detail})

@app.route('/api/parlays', methods=['GET'])
@login_required
def api_get_parlays():
    """API endpoint to get parlay opportunities"""
    try:
        conn = pymysql.connect(**DB_CONFIG_DICT)
        cursor = conn.cursor()
        
        # Get parlays with their legs
        cursor.execute("""
            SELECT 
                p.parlay_hash,
                p.contest_type,
                p.parlay_probability,
                p.contest_ev_percent,
                p.break_even_probability,
                p.edge_over_breakeven,
                p.meets_minimum,
                GROUP_CONCAT(
                    CONCAT_WS('|', 
                        pl.leg_number,
                        pl.player_name,
                        pl.market,
                        pl.line,
                        pl.ou,
                        pl.true_probability,
                        pl.sport
                    ) ORDER BY pl.leg_number SEPARATOR ';;'
                ) as legs_data
            FROM parlays p
            JOIN parlay_legs pl ON p.parlay_hash = pl.parlay_hash
            WHERE p.meets_minimum = 1
            GROUP BY p.parlay_hash
            ORDER BY p.contest_ev_percent DESC
            LIMIT 50
        """)
        
        parlays = []
        for row in cursor.fetchall():
            legs = []
            if row['legs_data']:
                for leg_str in row['legs_data'].split(';;'):
                    parts = leg_str.split('|')
                    if len(parts) >= 7:
                        legs.append({
                            'leg_number': int(parts[0]),
                            'player_name': parts[1],
                            'market': parts[2],
                            'line': float(parts[3]),
                            'ou': parts[4],
                            'true_probability': float(parts[5]),
                            'sport': parts[6]
                        })
            
            parlays.append({
                'parlay_hash': row['parlay_hash'],
                'contest_type': row['contest_type'],
                'parlay_probability': float(row['parlay_probability']),
                'contest_ev_percent': float(row['contest_ev_percent']),
                'break_even_probability': float(row['break_even_probability']),
                'edge_over_breakeven': float(row['edge_over_breakeven']),
                'legs': legs
            })
        
        conn.close()
        return jsonify({"success": True, "parlays": parlays})
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return jsonify({"success": False, "message": f"Error fetching parlays: {str(e)}", "detail": error_detail})

if __name__ == '__main__':
    print("Starting Bloomberg Terminal Style Flask application...")
    app.run(debug=True, port=5003)