"""
NFL/NCAAF Player Props Correlation Rules
Focused on QB-anchored correlations for parlay generation
"""

from decimal import Decimal

# Core correlation values for football player props
CORRELATION_VALUES = {
    # QB-WR1 Yards: Strong correlation
    'qb_wr1_yards': Decimal('0.70'),

    # QB-WR2 Yards: Moderate-strong correlation
    'qb_wr2_yards': Decimal('0.55'),

    # QB-WR3 Yards: Moderate correlation
    'qb_wr3_yards': Decimal('0.40'),

    # QB-TE Yards: Moderate correlation
    'qb_te_yards': Decimal('0.50'),

    # QB-RB Yards: Low-moderate correlation
    'qb_rb_yards': Decimal('0.35'),

    # QB-WR/TE/RB Receptions: Moderate correlation
    'qb_receiver_receptions': Decimal('0.60'),

    # No correlation
    'independent': Decimal('0.0')
}

# NFL/NCAAF Correlation Matrix - QB as Anchor
# Format: (qb_market, receiver_market, receiver_position) -> correlation_type

FOOTBALL_CORRELATIONS = {
    # QB PASS YARDS CORRELATIONS
    # Positive correlations (Over Pass Yds → Over Rec Yds)
    ('player_pass_yds', 'player_reception_yds', 'WR1'): 'qb_wr1_yards',
    ('player_pass_yds', 'player_reception_yds', 'WR2'): 'qb_wr2_yards',
    ('player_pass_yds', 'player_reception_yds', 'WR3'): 'qb_wr3_yards',
    ('player_pass_yds', 'player_reception_yds', 'TE'): 'qb_te_yards',
    ('player_pass_yds', 'player_reception_yds', 'RB'): 'qb_rb_yards',

    # QB PASS YARDS → RECEPTIONS CORRELATIONS (NCAAF specific - Splash has Receptions but not Pass Comp for NCAAF)
    # Positive correlations (Over Pass Yds → Over Receptions)
    ('player_pass_yds', 'player_receptions', 'WR1'): 'qb_receiver_receptions',
    ('player_pass_yds', 'player_receptions', 'WR2'): 'qb_receiver_receptions',
    ('player_pass_yds', 'player_receptions', 'WR3'): 'qb_receiver_receptions',
    ('player_pass_yds', 'player_receptions', 'TE'): 'qb_receiver_receptions',
    ('player_pass_yds', 'player_receptions', 'RB'): 'qb_receiver_receptions',

    # QB PASS COMPLETIONS CORRELATIONS (NFL only)
    # Positive correlations (Over Pass Comp → Over Receptions)
    ('player_pass_completions', 'player_receptions', 'WR1'): 'qb_receiver_receptions',
    ('player_pass_completions', 'player_receptions', 'WR2'): 'qb_receiver_receptions',
    ('player_pass_completions', 'player_receptions', 'WR3'): 'qb_receiver_receptions',
    ('player_pass_completions', 'player_receptions', 'TE'): 'qb_receiver_receptions',
    ('player_pass_completions', 'player_receptions', 'RB'): 'qb_receiver_receptions',
}

def get_correlation_score(qb_prop, receiver_prop):
    """
    Get correlation score between QB anchor and receiver prop

    Args:
        qb_prop: Dict with keys: market, ou, player_name, team, position_football
        receiver_prop: Dict with keys: market, ou, player_name, team, position_football

    Returns:
        Decimal: Correlation score
    """
    # Check if same game
    if not _is_same_game(qb_prop, receiver_prop):
        return CORRELATION_VALUES['independent']

    # Get receiver position
    receiver_position = receiver_prop.get('position_football')
    if not receiver_position:
        return CORRELATION_VALUES['independent']

    # Get correlation from matrix
    correlation_key = (qb_prop['market'], receiver_prop['market'], receiver_position)

    if correlation_key in FOOTBALL_CORRELATIONS:
        correlation_type = FOOTBALL_CORRELATIONS[correlation_key]
        base_correlation = CORRELATION_VALUES[correlation_type]

        # Football correlations are all positive (same direction)
        if qb_prop['ou'] == receiver_prop['ou']:
            return base_correlation
        else:
            return CORRELATION_VALUES['independent']

    return CORRELATION_VALUES['independent']

def get_correlated_markets(qb_market):
    """
    Get all markets that correlate with the QB market

    Args:
        qb_market: The QB's market (e.g., 'player_pass_yds', 'player_pass_completions')

    Returns:
        Dict: {receiver_market: {position: correlation_value}}
    """
    correlated_markets = {}

    for (qb_mkt, receiver_mkt, position), corr_type in FOOTBALL_CORRELATIONS.items():
        if qb_mkt == qb_market:
            corr_value = CORRELATION_VALUES[corr_type]

            if receiver_mkt not in correlated_markets:
                correlated_markets[receiver_mkt] = {}

            correlated_markets[receiver_mkt][position] = corr_value

    return correlated_markets

def _is_same_game(prop1, prop2):
    """Check if two props are from the same game"""
    return (prop1.get('home') == prop2.get('home') and
            prop1.get('away') == prop2.get('away'))

def _are_same_team(prop1, prop2):
    """Check if two props are from the same team"""
    # In football, QB and receivers should be on the same team for positive correlation
    return prop1.get('team') == prop2.get('team')

def get_correlation_type(qb_market):
    """
    Get the correlation type name for display

    Args:
        qb_market: The QB's market

    Returns:
        str: 'yards' or 'completions'
    """
    if qb_market == 'player_pass_yds':
        return 'yards'
    elif qb_market == 'player_pass_completions':
        return 'completions'
    return 'unknown'

def format_correlation_display(correlation_value):
    """Format correlation value for display"""
    if correlation_value >= 0.65:
        return "Strong"
    elif correlation_value >= 0.50:
        return "Moderate-Strong"
    elif correlation_value >= 0.35:
        return "Moderate"
    elif correlation_value > 0:
        return "Weak"
    else:
        return "Independent"

# Correlation descriptions for UI
CORRELATION_DESCRIPTIONS = {
    # QB pass yards correlations
    ('player_pass_yds', 'player_reception_yds', 'WR1'): "QB throws yards → WR1 catches yards",
    ('player_pass_yds', 'player_reception_yds', 'WR2'): "QB throws yards → WR2 catches yards",
    ('player_pass_yds', 'player_reception_yds', 'WR3'): "QB throws yards → WR3 catches yards",
    ('player_pass_yds', 'player_reception_yds', 'TE'): "QB throws yards → TE catches yards",
    ('player_pass_yds', 'player_reception_yds', 'RB'): "QB throws yards → RB catches yards",

    # QB pass yards → receptions correlations (NCAAF)
    ('player_pass_yds', 'player_receptions', 'WR1'): "QB throws yards → WR1 catches",
    ('player_pass_yds', 'player_receptions', 'WR2'): "QB throws yards → WR2 catches",
    ('player_pass_yds', 'player_receptions', 'WR3'): "QB throws yards → WR3 catches",
    ('player_pass_yds', 'player_receptions', 'TE'): "QB throws yards → TE catches",
    ('player_pass_yds', 'player_receptions', 'RB'): "QB throws yards → RB catches",

    # QB completions correlations (NFL)
    ('player_pass_completions', 'player_receptions', 'WR1'): "QB completes passes → WR1 catches",
    ('player_pass_completions', 'player_receptions', 'WR2'): "QB completes passes → WR2 catches",
    ('player_pass_completions', 'player_receptions', 'WR3'): "QB completes passes → WR3 catches",
    ('player_pass_completions', 'player_receptions', 'TE'): "QB completes passes → TE catches",
    ('player_pass_completions', 'player_receptions', 'RB'): "QB completes passes → RB catches",
}

def get_correlation_description(qb_prop, receiver_prop):
    """Get human-readable description of correlation"""
    receiver_position = receiver_prop.get('position_football')
    if not receiver_position:
        return "Unknown correlation"

    key = (qb_prop['market'], receiver_prop['market'], receiver_position)
    return CORRELATION_DESCRIPTIONS.get(key, "Correlated props")
