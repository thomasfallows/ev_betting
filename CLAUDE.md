# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a sports betting analysis tool that identifies Positive Expected Value (+EV) betting opportunities by comparing odds between traditional sportsbooks and Splash Sports. The project supports both MLB and WNBA player props.

## Key Commands

### Running the Application
```bash
# Install dependencies
pip install -r requirements.txt

# Run the Flask application (multiple entry points available)
python run.py
# Alternative: python Backend/app.py
# Alternative: python start_server.py

# Application runs on http://localhost:5001
```

### Data Pipeline Execution

#### Via Web Interface:
1. Navigate to http://localhost:5001
2. Click "Execute All Scripts" button to run data pipeline sequentially

#### Via Command Line:
```bash
# 1. Scrape Splash Sports data (MLB + WNBA)
python Backend/data_scripts/splash_scraper.py

# 2. Fetch odds from sportsbooks (driven by Splash props)
python Backend/data_scripts/odds_api.py

# 3. Calculate EV and generate report
python Backend/data_scripts/create_report.py

# Optional: Run EV analysis with advanced scoring
python Backend/data_scripts/splash_ev_analysis.py
```

### Database Operations
```bash
# Run database migrations (adds sport columns if missing)
python Backend/data_scripts/database_migration.py
```

## Architecture & Code Flow

### Database Schema (MySQL)
- `player_props`: Sportsbook odds with columns: player_name, normalized_name, market, line, ou, book, dxodds, home, away, game_id
- `splash_props`: Splash Sports props with columns: player_name, normalized_name, market, line, game_date, home, away, sport (default: 'mlb')
- `ev_opportunities`: Calculated EV opportunities with fair probability, splash probability, and EV percentage
- `ev_report`: Legacy table name (check if still in use)

### Core EV Algorithm (Updated with De-vigging)
Located in `Backend/data_scripts/create_report.py`:
1. **De-vigging Process**:
   - Finds props with BOTH Over and Under odds from same sportsbook
   - Calculates de-vigged probabilities: `true_prob = raw_prob / (over_prob + under_prob)`
   - Averages de-vigged probabilities across all books with both sides
   - One-sided props (missing Over or Under) are excluded from EV calculations
2. Compares against Splash's implied probability: `SPLASH_IMPLIED_PROB = (1/3)^(1/2) ≈ 0.577`
3. EV% = (de-vigged_probability - splash_probability) * 100
4. Only processes EXACT matches: same player, market, line
5. **Visual Indicators** (Raw Odds page): One-sided props highlighted in yellow background

### Data Flow Architecture
1. **Splash-Driven Collection**: `splash_scraper.py` collects all available props from Splash API
2. **Targeted Odds Fetching**: `odds_api.py` reads Splash props and fetches matching odds from The Odds API
3. **EV Calculation**: `create_report.py` joins data and calculates opportunities
4. **Web Display**: Flask app serves results via Bloomberg Terminal-styled interface

## Critical Constants & Configuration

### SPLASH_IMPLIED_PROB
- Location: `Backend/data_scripts/create_report.py`
- Value: `Decimal(1/3)**(Decimal(1/2))` (~0.577)
- **DO NOT MODIFY** - Core to EV calculation

### Market Name Mappings
Defined in `Backend/config.py` and used via SQL CASE statements:

**MLB Markets:**
- pitcher_ks/strikeouts → pitcher_strikeouts
- earned_runs → pitcher_earned_runs
- allowed_hits/hits_allowed → pitcher_hits_allowed
- total_bases → batter_total_bases
- hits → batter_hits
- singles → batter_singles
- runs → batter_runs_scored
- rbis → batter_rbis
- outs/total_outs → pitcher_outs

**WNBA Markets:**
- points → player_points
- rebounds → player_rebounds
- pts+reb+asts → player_points_rebounds_assists
- pts+reb → player_points_rebounds
- pts+asts → player_points_assists
- assists → player_assists
- 3-PT Made → player_threes


### API Configuration
- **The Odds API**: Rate limited to 0.5s between calls (see `API_DELAY` in `odds_api.py`)
- **Splash API**: Supports pagination with 100 props per request
- **US Sportsbooks Only**: DraftKings, FanDuel, Caesars, BetMGM, PointsBet, Bet365, ESPN Bet, BetRivers, Fanatics

## Important Implementation Details

1. **Full Refresh Strategy**: Tables are truncated on each pipeline run (by design for data freshness)

2. **Expected EV Values**: With proper de-vigging, typical positive EV opportunities range from 0.1% to 3%. Values above 5% are rare and should be verified.

3. **Player Name Normalization**: Both systems normalize names to handle accents/special characters

4. **Database Collation**: Uses `utf8mb4_general_ci` for case-insensitive joins

5. **Time Zone**: America/Halifax (Atlantic Time) for all game scheduling

6. **Star Player Scoring**: `splash_ev_analysis.py` includes public appeal scoring for notable players

7. **Multi-Sport Support**: System architecture supports MLB and WNBA with easy extension

## Working State (Do Not Break)
Last verified: [date]
- splash_scraper.py: WORKING - fetches MLB and WNBA props
- odds_api.py: WORKING - gets odds for all props
- create_report.py: WORKING - calculates EV correctly
- Database schema: STABLE - has sport column

9.  KNOWN ISSUES (DO NOT REINTRODUCE)
- Do NOT remove the sport column from any table
- Do NOT change the SPLASH_IMPLIED_PROB calculation
- Do NOT modify the devigging formula without updating all files

10. CURRENT FOCUS
- Adding correlation analysis
- DO NOT touch working scrapers while doing this

11. 🧪 VERIFICATION COMMANDS
Always run these after changes to ensure nothing broke:

## Test scrapers:
   ```bash
   python data_scripts/splash_scraper.py
   # Should see: "Props by sport: MLB: X props, WNBA: Y props"

   python data_scripts/odds_api.py
   # Should see: "Found X unique props from Splash"

   python data_scripts/create_report.py
   # Should see: "Top 5 EV opportunities"

If ANY of these fail, REVERT changes immediately.



## Environment Configuration

Create `.env` file in project root:
```
ODDS_API_KEY=your_api_key_here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=MyDatabase
```

**Note**: Some scripts may still have hardcoded credentials - migration to python-dotenv is ongoing.

## Web Interface Routes

- `/` - Main dashboard with EV opportunities table
- `/api/execute` - Runs complete data pipeline
- `/api/execute/<script>` - Run individual script (splash_scraper, odds_api, create_report)
- `/api/ev_data` - Returns current EV opportunities as JSON
- `/api/market_comparison` - Detailed odds comparison for specific props
- `/api/test_db` - Database connection test

