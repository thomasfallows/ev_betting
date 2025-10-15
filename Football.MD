NFL/NCAAF Correlation Parlays - Complete Implementation Specification
PROJECT OVERVIEW
Objective
Extend the existing EV betting system to support NFL and NCAAF player prop correlations, identifying mathematical relationships between quarterback and skill position players to generate positive expected value parlays against Splash Sports' implied probabilities.
Core Principle
Unlike predicting game outcomes, this system identifies statistical correlations between player props and exploits pricing inefficiencies between Vegas sportsbooks (true probability via de-vigging) and Splash Sports (implied probability of 57.74%).
SYSTEM ARCHITECTURE
1. DATA PIPELINE
1.1 Market Mapping (CRITICAL)

**NFL Markets (Full Support):**
Pass Yds     → player_pass_yds
Pass Comp    → player_pass_completions
Rec Yds      → player_reception_yds
Rec          → player_receptions

**NCAAF Markets (Different Structure):**
Pass Yds     → player_pass_yds (QB only)
Rec Yds      → player_reception_yds (Receivers)
Rec          → player_receptions (Receivers)

**NOTE:** Splash Sports does NOT offer Pass Completions market for NCAAF QBs.
NCAAF uses QB Pass Yards as the anchor, which correlates with BOTH Receiver Rec Yards AND Receiver Receptions.

Complete Odds API Market List for Reference:
player_pass_yds            - Pass Yards (Over/Under) - NFL + NCAAF
player_pass_completions    - Pass Completions (Over/Under) - NFL ONLY
player_reception_yds       - Reception Yards (Over/Under) - NFL + NCAAF
player_receptions          - Receptions (Over/Under) - NFL ONLY

1.2 Data Collection Flow

Splash Scraper Enhancement

Modify splash_scraper.py to detect NFL/NCAAF props
Filter to ONLY collect: Pass Yds, Pass Comp, Rec Yds, Rec
Store sport type ('nfl' or 'ncaaf') in database


Odds API Enhancement

Modify odds_api.py to fetch NFL/NCAAF games
Use same sportsbooks as MLB (DraftKings, FanDuel, BetMGM, Caesars, BetRivers, Fanatics, ESPN BET, PointsBet)
Map markets correctly using the mapping above
Calculate de-vigged probabilities using existing methodology


Matching Logic

Use normalized player names
Match by player name + market + line
Track number of books per prop for confidence scoring



2. CORRELATION DEFINITIONS
2.1 Correlation Types by Sport

**NFL: Two Correlation Types (Separate Stacks)**
- Type 1: QB Pass Yards → Receiver Rec Yards
- Type 2: QB Pass Completions → Receiver Receptions

**NCAAF: One QB Anchor, Multiple Receiver Props** (Splash doesn't offer Pass Completions for QBs)
- QB Pass Yards (Anchor) → correlates with BOTH:
  - Receiver Rec Yards
  - Receiver Receptions

Type 1: QB-WR Yards Correlation (NFL + NCAAF)
pythonYARDS_CORRELATIONS = {
    'qb_pass_yards': {
        'wr1_rec_yards': 0.70,  # WR1: 60+ yard line
        'wr2_rec_yards': 0.55,  # WR2: 40-60 yard line
        'wr3_rec_yards': 0.40,  # WR3: Under 40 yard line
        'te_rec_yards': 0.50,   # Any TE receiving yards
        'rb_rec_yards': 0.35    # Any RB receiving yards
    }
}

Type 2: QB-Receiver Completions Correlation (NFL ONLY)
pythonCOMPLETIONS_CORRELATIONS = {
    'qb_pass_completions': {
        'wr_receptions': 0.60,
        'te_receptions': 0.60,
        'rb_receptions': 0.60
    }
}
2.2 Position Identification Rules
Wide Receivers (by receiving yards line):

WR1: Line ≥ 60 yards
WR2: Line 40-59 yards
WR3: Line < 40 yards

Other Positions:

TE: Identified by player name containing "TE" or known TE names
RB: Identified by player name containing "RB" or known RB names
If position unclear: Treat as generic receiver with 0.50 correlation

3. PARLAY GENERATION LOGIC
3.1 Stack Structure
Each "stack" consists of:

Anchor: QB with one of three prop types (Pass Yards/TDs/Completions)
Correlated Props: WR/TE/RB props from SAME TEAM
Minimum: QB + 1 correlated prop
Maximum Display: QB + all available correlated props (user selects up to 6)

3.2 Parlay Construction Rules

Team Requirements

Minimum: 1 player from each of 2 teams
Maximum: 6 total legs
Can combine multiple players from same team


Correlation Requirements

Every leg must be correlated to at least one other leg
Show separate stacks for each team's QB
User combines stacks to create full parlays


Valid Parlay Examples

   4-leg: Team A QB + Team A WR1 + Team B QB + Team B WR1
   5-leg: Team A QB + Team A WR1 + Team A WR2 + Team B QB + Team B WR1
   6-leg: Team A QB + Team A WR1 + Team A WR2 + Team B QB + Team B WR1 + Team B WR2
3.3 Ranking System
Within each correlation type:

Sort QBs by EV% (highest first)
For each QB, show all correlated props
Display book count for confidence assessment
Show correlation strength for each pairing

4. DATABASE SCHEMA UPDATES
4.1 Extend Existing Tables
player_props table additions:
sql-- Already has sport column
-- Ensure normalized_name is properly indexed
-- No structural changes needed, just ensure NFL/NCAAF data flows through
4.2 New File Structure
Create nfl_correlation_parlays.py:
pythonclass NFLCorrelationParlayGenerator:
    def __init__(self, props, sport='nfl'):
        self.props = props
        self.sport = sport  # 'nfl' or 'ncaaf'
        self.correlation_types = ['yards', 'completions']
        
    def identify_position(self, player_name, market, line):
        """Determine if WR1/WR2/WR3/TE/RB based on line value"""
        
    def get_correlation_strength(self, qb_prop, receiver_prop):
        """Return correlation coefficient based on types"""
        
    def generate_stacks(self):
        """Generate all QB-anchored stacks by correlation type"""
        
    def format_display_data(self):
        """Format stacks for web interface display"""
5. WEB INTERFACE UPDATES
5.1 Navigation Structure
EV OPS Tab
├── Singles
└── Parlays
    ├── MLB (existing)
    ├── NFL (new)
    └── NCAAF (new)
5.2 Display Format

**NFL Correlation View (2-column layout):**
┌─────────────────────────────────────────────────────────────┐
│                     NFL CORRELATIONS                         │
├──────────────┬──────────────────────────────────────────────┤
│   YARDS      │           COMPLETIONS                        │
├──────────────┼──────────────────────────────────────────────┤
│ Stack #1     │ Stack #1                                     │
│ P.Mahomes    │ J.Burrow                                     │
│ Pass: O 285.5│ Comp: O 24.5                                 │
│ EV: +3.1%    │ EV: +2.2%                                    │
│ Books: 8     │ Books: 6                                     │
│              │                                              │
│ Correlated:  │ Correlated:                                  │
│ T.Kelce      │ J.Chase                                      │
│ Rec: O 65.5  │ Rec: O 6.5                                   │
│ EV: +1.2%    │ EV: +1.5%                                    │
│ Corr: 0.50   │ Corr: 0.60                                   │
│ Books: 5     │ Books: 6                                     │
│              │                                              │
│ T.Hill       │ T.Higgins                                    │
│ Rec: O 85.5  │ Rec: O 5.5                                   │
│ EV: -0.5%    │ EV: +0.3%                                    │
│ Corr: 0.70   │ Corr: 0.60                                   │
│ Books: 6     │ Books: 5                                     │
└──────────────┴──────────────────────────────────────────────┘

**NCAAF Correlation View (1-column layout - QB Pass Yards Anchor):**
┌──────────────────────────────────────────┐
│          NCAAF CORRELATIONS              │
├──────────────────────────────────────────┤
│     QB PASS YARDS + RECEIVER PROPS       │
├──────────────────────────────────────────┤
│ Stack #1                                 │
│ C.Williams (Ohio State)                  │
│ Pass Yds: O 275.5                        │
│ EV: +2.8%                                │
│ Books: 7                                 │
│                                          │
│ Correlated:                              │
│ M.Harrison Jr (WR1)                      │
│ Rec Yds: O 88.5                          │
│ EV: +1.5%                                │
│ Corr: 0.70                               │
│ Books: 6                                 │
│                                          │
│ M.Harrison Jr (WR1)                      │
│ Receptions: O 6.5                        │
│ EV: +1.2%                                │
│ Corr: 0.60                               │
│ Books: 5                                 │
│                                          │
│ E.Egbuka (WR2)                           │
│ Rec Yds: O 55.5                          │
│ EV: +0.8%                                │
│ Corr: 0.55                               │
│ Books: 5                                 │
└──────────────────────────────────────────┘

**Note:** Each receiver can have BOTH Rec Yds and Receptions props correlated with the QB's Pass Yards.

5.3 User Interaction

User clicks on props to select them for a parlay
Selected props highlight
Bottom panel shows:

Combined parlay probability
Total EV%
Correlation matrix between selected legs
"Build Parlay" button



6. IMPLEMENTATION SPECIFICATIONS
6.1 Core Functions
pythondef fetch_nfl_ncaaf_props():
    """
    1. Query splash_props for sport in ('nfl', 'ncaaf')
    2. Filter to only correlation markets
    3. Return organized by team and game
    """

def calculate_correlations(qb_prop, skill_prop):
    """
    1. Identify correlation type (yards/tds/completions)
    2. Identify skill position (WR1/WR2/WR3/TE/RB)
    3. Return correlation coefficient
    """

def generate_correlation_stacks(props):
    """
    1. Find all QBs with positive EV
    2. For each QB, find correlated skill players
    3. Group by correlation type
    4. Return sorted stacks
    """

def validate_parlay(selected_props):
    """
    1. Check minimum 2 teams represented
    2. Check all props are correlated
    3. Check no duplicate players
    4. Return validation result
    """
6.2 API Endpoints
python@app.route('/api/nfl-correlation-stacks', methods=['GET'])
def get_nfl_stacks():
    """Return all NFL correlation stacks grouped by type"""
    
@app.route('/api/ncaaf-correlation-stacks', methods=['GET'])
def get_ncaaf_stacks():
    """Return all NCAAF correlation stacks grouped by type"""
    
@app.route('/api/build-nfl-parlay', methods=['POST'])
def build_nfl_parlay():
    """Validate and create NFL parlay from selected props"""
7. SPECIAL CONSIDERATIONS
7.1 Edge Case Handling

Missing Correlations

If QB has props but no skill players: Don't display stack
If only one team has props: Still display (can combine with other games)
If no books have odds: Show with 0% EV and 0 books indicator


Data Quality

Always show number of books
Flag props with < 3 books as "Low Confidence"
Use same de-vigging methodology as MLB



7.2 Performance Optimizations

Cache correlation calculations
Pre-compute position identifications
Batch database queries by sport and game

8. TESTING REQUIREMENTS
8.1 Data Validation

Verify market mapping is correct
Ensure position identification works correctly
Validate correlation coefficients are applied properly

8.2 Parlay Validation

Test minimum team requirements
Verify no duplicate players allowed
Ensure all correlations are calculated correctly

8.3 Integration Testing

Confirm NFL/NCAAF data flows through existing pipeline
Verify de-vigging calculations work for football
Test web interface displays correctly

9. DEPLOYMENT CHECKLIST

✅ Modify splash_scraper.py to handle NFL/NCAAF
✅ Update odds_api.py with NFL/NCAAF markets
✅ Create nfl_correlation_parlays.py
✅ Add NFL/NCAAF sections to web interface
✅ Test with real NFL data
✅ Test with real NCAAF data
✅ Verify EV calculations are accurate
✅ Deploy to production