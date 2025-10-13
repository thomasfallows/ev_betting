import sys
sys.path.append('Backend')
sys.path.append('Backend/data_scripts')
sys.path.append('Backend/config')

import pymysql
from Backend.config import DB_CONFIG_DICT
from Backend.data_scripts.qb_anchored_parlays import QBAnchoredParlayGenerator

# Get props from database
conn = pymysql.connect(**DB_CONFIG_DICT)
cursor = conn.cursor()

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

# Convert to format expected by generator
props_list = []
for prop in all_props:
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

print(f'Testing with {len(props_list)} props')
print()

# Generate stacks
generator = QBAnchoredParlayGenerator(props_list, sport='nfl')
display_data = generator.generate_display_data(limit=5)

print('YARDS CORRELATION STACKS:')
print('=' * 80)
for i, stack in enumerate(display_data['yards_stacks'], 1):
    qb = stack['qb']
    print(f"Stack {i}: {qb['player_name']} - {qb['ou']} {qb['line']} yards ({qb['ev']:+.1f}% EV) | Books: {qb['book_count']}")
    print(f"  Game: {qb['away']} @ {qb['home']}")
    if stack['receivers']:
        print(f"  Correlated receivers ({len(stack['receivers'])}):")
        for receiver in stack['receivers'][:3]:
            print(f"    {receiver['position']:4} {receiver['player_name']:20} | {receiver['ou']} {receiver['line']:5.1f} | EV: {receiver['ev']:+.1f}% | Corr: {receiver['correlation_score']:.2f}")
    else:
        print('  No correlated receivers')
    print()

print()
print('COMPLETIONS CORRELATION STACKS:')
print('=' * 80)
for i, stack in enumerate(display_data['completions_stacks'], 1):
    qb = stack['qb']
    print(f"Stack {i}: {qb['player_name']} - {qb['ou']} {qb['line']} comp ({qb['ev']:+.1f}% EV) | Books: {qb['book_count']}")
    print(f"  Game: {qb['away']} @ {qb['home']}")
    if stack['receivers']:
        print(f"  Correlated receivers ({len(stack['receivers'])}):")
        for receiver in stack['receivers'][:3]:
            print(f"    {receiver['position']:4} {receiver['player_name']:20} | {receiver['ou']} {receiver['line']:5.1f} | EV: {receiver['ev']:+.1f}% | Corr: {receiver['correlation_score']:.2f}")
    else:
        print('  No correlated receivers')
    print()
