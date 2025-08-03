import pymysql
from config import DB_CONFIG_DICT
from data_scripts.create_report_parlay import calculate_devigged_probability
from data_scripts.pitcher_anchored_parlays import PitcherAnchoredParlayGenerator
from decimal import Decimal

conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

# Get all props just like create_report_parlay does
sql_query = """
SELECT 
    sp.player_name,
    sp.normalized_name,
    sp.market as splash_market,
    sp.line,
    pp.book,
    pp.ou,
    pp.dxodds,
    pp.home,
    pp.away,
    sp.team_abbr as team,
    sp.sport
FROM splash_props sp
JOIN player_props pp ON (
    sp.normalized_name = pp.normalized_name
    AND sp.line = pp.line
    AND pp.market = (CASE sp.market 
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
        ELSE 'no_match'
    END)
    AND ABS(DATEDIFF(sp.game_date, pp.gamedate)) <= 1
)
WHERE pp.dxodds IS NOT NULL
ORDER BY sp.player_name, sp.market, sp.line, pp.book, pp.ou
"""

cursor.execute(sql_query)
all_matches = cursor.fetchall()
print(f"Found {len(all_matches)} matches")

# Group props by player/market/line
props_grouped = {}
for match in all_matches:
    key = (match['player_name'], match['normalized_name'], match['splash_market'], match['line'])
    if key not in props_grouped:
        props_grouped[key] = {
            'home': match['home'],
            'away': match['away'],
            'sport': match.get('sport', 'mlb'),
            'team': match.get('team'),
            'books_data': []
        }
    props_grouped[key]['books_data'].append((match['book'], match['dxodds'], match['ou']))

print(f"Found {len(props_grouped)} unique props")

# Check pitcher props
pitcher_count = 0
for (player_name, normalized_name, market, line), prop_data in props_grouped.items():
    if 'pitcher' in market or market in ['strikeouts', 'earned_runs', 'allowed_hits', 'hits_allowed', 'outs', 'total_outs']:
        pitcher_count += 1
        print(f"Pitcher prop: {player_name} - {market} {line}")

print(f"\nTotal pitcher props: {pitcher_count}")

# Process props and check what we get
all_props = []
one_sided_count = 0

for (player_name, normalized_name, market, line), prop_data in props_grouped.items():
    # Calculate de-vigged probability
    over_prob, under_prob, has_both_sides = calculate_devigged_probability(prop_data['books_data'])
    
    if not has_both_sides:
        one_sided_count += 1
        continue
    
    # Calculate EV for both sides
    SPLASH_IMPLIED_PROB = Decimal(1/3)**(Decimal(1/2))
    for side, true_prob in [('O', over_prob), ('U', under_prob)]:
        ev_percentage = (true_prob - SPLASH_IMPLIED_PROB) * 100
        
        # Add ALL props (even negative EV)
        all_props.append({
            'player_name': player_name,
            'normalized_name': normalized_name,
            'market': market,
            'line': line,
            'ou': side,
            'true_probability': float(true_prob),
            'ev_percentage': float(ev_percentage),
            'home': prop_data['home'],
            'away': prop_data['away'],
            'sport': prop_data['sport'],
            'team': prop_data['team']
        })

print(f"\nAfter de-vigging: {len(all_props)} prop sides")

# Test the generator
generator = PitcherAnchoredParlayGenerator(all_props)
print(f"\nGames found: {len(generator.games)}")
for game_key, game_data in generator.games.items():
    print(f"  {game_key}: {len(game_data['pitchers'])} pitchers, {len(game_data['batters'])} batters")

anchors = generator.find_pitcher_anchors()
print(f"\nAnchors found: {len(anchors)}")
for i, anchor_data in enumerate(anchors[:5]):
    anchor = anchor_data['prop']
    print(f"  {i+1}. {anchor['player_name']} - {anchor['market']} {anchor['ou']} {anchor['line']} ({anchor['ev_percentage']:.2f}% EV)")

cursor.close()
conn.close()