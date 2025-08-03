"""
Correlation rules for parlay generation
Defines relationships between different prop types
"""

from decimal import Decimal

# Correlation strength definitions
CORRELATION_STRENGTHS = {
    'strong_negative': Decimal('-0.7'),    # Highly inversely correlated
    'moderate_negative': Decimal('-0.4'),  # Moderately inversely correlated
    'weak_negative': Decimal('-0.2'),      # Slightly inversely correlated
    'independent': Decimal('0.0'),         # No correlation
    'weak_positive': Decimal('0.2'),       # Slightly correlated
    'moderate_positive': Decimal('0.4'),   # Moderately correlated
    'strong_positive': Decimal('0.7')      # Highly correlated - AVOID
}

# MLB-specific correlations
MLB_CORRELATIONS = {
    # Pitcher Strikeouts vs Opposing Team Hitting
    ('pitcher_strikeouts', 'O', 'batter_hits', 'O'): 'strong_negative',
    ('pitcher_strikeouts', 'O', 'batter_total_bases', 'O'): 'strong_negative',
    ('pitcher_strikeouts', 'O', 'batter_singles', 'O'): 'moderate_negative',
    ('pitcher_strikeouts', 'U', 'batter_hits', 'U'): 'moderate_negative',
    
    # Pitcher Performance vs Runs
    ('pitcher_earned_runs', 'U', 'batter_runs_scored', 'U'): 'moderate_negative',
    ('pitcher_earned_runs', 'O', 'batter_runs_scored', 'O'): 'moderate_positive',
    ('pitcher_hits_allowed', 'U', 'batter_hits', 'U'): 'strong_negative',
    ('pitcher_hits_allowed', 'O', 'batter_hits', 'O'): 'strong_positive',
    
    # Same Batter Correlations (AVOID THESE)
    ('batter_hits', 'O', 'batter_total_bases', 'O'): 'strong_positive',
    ('batter_hits', 'U', 'batter_total_bases', 'U'): 'strong_positive',
    ('batter_hits', 'O', 'batter_singles', 'O'): 'strong_positive',
    ('batter_runs_scored', 'O', 'batter_rbis', 'O'): 'moderate_positive',
    
    # Pitcher Efficiency
    ('pitcher_outs', 'O', 'batter_hits', 'U'): 'moderate_negative',
    ('pitcher_outs', 'O', 'pitcher_hits_allowed', 'U'): 'moderate_negative',
    
    # Game Flow Correlations
    ('pitcher_strikeouts', 'O', 'pitcher_earned_runs', 'U'): 'weak_negative',
    ('batter_hits', 'U', 'batter_strikeouts', 'O'): 'moderate_negative',
}

# WNBA-specific correlations
WNBA_CORRELATIONS = {
    # Usage-based correlations
    ('player_points', 'U', 'player_assists', 'O'): 'moderate_negative',
    ('player_points', 'O', 'player_assists', 'U'): 'weak_negative',
    ('player_rebounds', 'O', 'player_assists', 'O'): 'weak_negative',
    
    # Combined stat correlations (AVOID)
    ('player_points', 'O', 'player_points_rebounds_assists', 'O'): 'strong_positive',
    ('player_points', 'U', 'player_points_rebounds_assists', 'U'): 'strong_positive',
    ('player_rebounds', 'O', 'player_points_rebounds_assists', 'O'): 'strong_positive',
    ('player_assists', 'O', 'player_points_rebounds_assists', 'O'): 'strong_positive',
    ('player_points', 'O', 'player_points_rebounds', 'O'): 'strong_positive',
    ('player_points', 'O', 'player_points_assists', 'O'): 'strong_positive',
    
    # Playing time correlations
    ('player_points', 'U', 'player_rebounds', 'U'): 'weak_positive',
    ('player_threes', 'O', 'player_points', 'O'): 'moderate_positive',
}

# General correlation rules (apply to all sports)
GENERAL_CORRELATIONS = {
    # Team performance affects all players
    'same_team_same_direction': 'weak_positive',      # Both overs or both unders on same team
    'same_team_opposite_direction': 'independent',    # One over, one under on same team
    'opposing_teams_same_stat': 'weak_negative',      # Opposing teams, same stat type
    'same_game_factor': 'weak_positive',              # Just being in same game
}

def get_correlation_score(leg1, leg2, sport='mlb'):
    """
    Calculate correlation score between two prop legs
    
    Args:
        leg1: Dict with keys: player_name, market, ou, home, away, team (optional)
        leg2: Dict with keys: player_name, market, ou, home, away, team (optional)
        sport: 'mlb' or 'wnba'
    
    Returns:
        Decimal: Correlation score between -1 and 1
    """
    # Check if same game
    same_game = (leg1['home'] == leg2['home'] and leg1['away'] == leg2['away'])
    
    if not same_game:
        return CORRELATION_STRENGTHS['independent']
    
    # Check sport-specific correlations
    correlation_map = MLB_CORRELATIONS if sport == 'mlb' else WNBA_CORRELATIONS
    
    # Direct lookup
    key = (leg1['market'], leg1['ou'], leg2['market'], leg2['ou'])
    if key in correlation_map:
        return CORRELATION_STRENGTHS[correlation_map[key]]
    
    # Reverse lookup (correlation is symmetric)
    reverse_key = (leg2['market'], leg2['ou'], leg1['market'], leg1['ou'])
    if reverse_key in correlation_map:
        return CORRELATION_STRENGTHS[correlation_map[reverse_key]]
    
    # Apply general rules if no specific correlation found
    if same_game:
        # Check if same player
        if leg1.get('player_name') == leg2.get('player_name'):
            # Same player, different props - usually correlated
            if leg1['ou'] == leg2['ou']:
                return CORRELATION_STRENGTHS['moderate_positive']
            else:
                return CORRELATION_STRENGTHS['weak_positive']
        
        # Check if same team (if team info available)
        if 'team' in leg1 and 'team' in leg2:
            if leg1['team'] == leg2['team']:
                if leg1['ou'] == leg2['ou']:
                    return CORRELATION_STRENGTHS['weak_positive']
                else:
                    return CORRELATION_STRENGTHS['independent']
        
        # Different players, same game - slight correlation
        return Decimal('0.1')  # Very weak positive
    
    return CORRELATION_STRENGTHS['independent']

def get_correlation_description(score):
    """Get human-readable description of correlation strength"""
    score = Decimal(str(score))
    
    if score <= Decimal('-0.6'):
        return "Strong Negative (Excellent hedge)"
    elif score <= Decimal('-0.3'):
        return "Moderate Negative (Good hedge)"
    elif score <= Decimal('-0.1'):
        return "Weak Negative (Slight hedge)"
    elif score <= Decimal('0.1'):
        return "Independent (No correlation)"
    elif score <= Decimal('0.3'):
        return "Weak Positive (Slight correlation)"
    elif score <= Decimal('0.6'):
        return "Moderate Positive (Avoid if possible)"
    else:
        return "Strong Positive (AVOID - High risk)"

def calculate_variance_reduction(correlation_score):
    """
    Calculate variance reduction factor based on correlation
    
    For 2-leg parlay with correlation ρ:
    Var(X+Y) = Var(X) + Var(Y) + 2ρ√(Var(X)Var(Y))
    
    Returns multiplier for variance (1.0 = no change, <1.0 = reduced variance)
    """
    # Simplified model assuming equal variance for both legs
    # Variance multiplier ≈ 1 + ρ
    return 1 + float(correlation_score)

def find_best_correlations(available_props, sport='mlb', correlation_type='negative'):
    """
    Find prop pairs with best correlations
    
    Args:
        available_props: List of prop dicts
        sport: 'mlb' or 'wnba'
        correlation_type: 'negative' or 'positive'
    
    Returns:
        List of tuples: (prop1, prop2, correlation_score)
    """
    correlations = []
    
    for i, prop1 in enumerate(available_props):
        for j, prop2 in enumerate(available_props[i+1:], i+1):
            score = get_correlation_score(prop1, prop2, sport)
            
            if correlation_type == 'negative' and score < 0:
                correlations.append((prop1, prop2, score))
            elif correlation_type == 'positive' and score > 0:
                correlations.append((prop1, prop2, score))
    
    # Sort by absolute correlation strength
    if correlation_type == 'negative':
        correlations.sort(key=lambda x: x[2])  # Most negative first
    else:
        correlations.sort(key=lambda x: x[2], reverse=True)  # Most positive first
    
    return correlations

# Examples of ideal negative correlation parlays
IDEAL_CORRELATION_EXAMPLES = {
    'mlb': [
        {
            'description': 'Ace pitcher dominance parlay',
            'leg1': {'market': 'pitcher_strikeouts', 'ou': 'O'},
            'leg2': {'market': 'batter_hits', 'ou': 'U', 'note': 'opposing team'},
            'reasoning': 'More strikeouts = fewer balls in play = fewer hits'
        },
        {
            'description': 'Low-scoring game parlay',
            'leg1': {'market': 'pitcher_earned_runs', 'ou': 'U'},
            'leg2': {'market': 'batter_runs_scored', 'ou': 'U', 'note': 'opposing team'},
            'reasoning': 'Pitcher limiting runs correlates with opposing team scoring less'
        },
        {
            'description': 'Pitcher efficiency parlay',
            'leg1': {'market': 'pitcher_outs', 'ou': 'O'},
            'leg2': {'market': 'pitcher_hits_allowed', 'ou': 'U'},
            'reasoning': 'Efficient pitcher gets more outs while allowing fewer hits'
        }
    ],
    'wnba': [
        {
            'description': 'Ball distributor parlay',
            'leg1': {'market': 'player_points', 'ou': 'U'},
            'leg2': {'market': 'player_assists', 'ou': 'O'},
            'reasoning': 'Player focusing on distributing rather than scoring'
        },
        {
            'description': 'Role player balance',
            'leg1': {'market': 'player_rebounds', 'ou': 'O'},
            'leg2': {'market': 'player_assists', 'ou': 'U'},
            'reasoning': 'Player focused on rebounding, less ball handling'
        }
    ]
}