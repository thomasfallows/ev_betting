"""
MLB Player Props Correlation Rules
Focused on pitcher-anchored correlations for parlay generation
"""

from decimal import Decimal

# Core correlation values for MLB player props
CORRELATION_VALUES = {
    # Strong Positive Correlations (0.35-0.45)
    'strong_positive': Decimal('0.40'),
    
    # Moderate Positive Correlations (0.25-0.35)  
    'moderate_positive': Decimal('0.30'),
    
    # Moderate Negative Correlations (-0.25 to -0.35)
    'moderate_negative': Decimal('-0.30'),
    
    # No correlation
    'independent': Decimal('0.0')
}

# MLB Correlation Matrix - Pitcher as Anchor
# Format: (anchor_market, batter_market) -> correlation_type
MLB_CORRELATIONS = {
    # PITCHER STRIKEOUTS (Ks) CORRELATIONS - supports both naming conventions
    # Negative correlations (Over Ks → Under batting stats)
    ('pitcher_strikeouts', 'batter_hits'): 'moderate_negative',        # -0.20 to -0.30
    ('pitcher_strikeouts', 'batter_total_bases'): 'moderate_negative', # -0.25 to -0.35
    ('pitcher_strikeouts', 'batter_singles'): 'moderate_negative',     # -0.15 to -0.25
    ('strikeouts', 'hits'): 'moderate_negative',                       # -0.20 to -0.30
    ('strikeouts', 'total_bases'): 'moderate_negative',                # -0.25 to -0.35
    ('strikeouts', 'singles'): 'moderate_negative',                    # -0.15 to -0.25
    
    # Positive correlations  
    ('pitcher_strikeouts', 'pitcher_outs'): 'moderate_positive',       # 0.30-0.40
    ('strikeouts', 'outs'): 'moderate_positive',                       # 0.30-0.40
    ('strikeouts', 'total_outs'): 'moderate_positive',                 # 0.30-0.40
    
    # PITCHER EARNED RUNS CORRELATIONS
    # Positive correlations (Over ER → Over batting stats)
    ('pitcher_earned_runs', 'batter_runs_scored'): 'strong_positive',  # 0.35-0.45
    ('pitcher_earned_runs', 'batter_rbis'): 'strong_positive',         # 0.35-0.45
    ('earned_runs', 'runs'): 'strong_positive',                        # 0.35-0.45
    ('earned_runs', 'rbis'): 'strong_positive',                        # 0.35-0.45
    
    # PITCHER ALLOWED HITS CORRELATIONS
    # Positive correlations (Over Allowed Hits → Over batting stats)
    ('pitcher_hits_allowed', 'batter_hits'): 'strong_positive',        # 0.35-0.45
    ('pitcher_hits_allowed', 'batter_total_bases'): 'moderate_positive', # 0.25-0.35
    ('pitcher_hits_allowed', 'batter_singles'): 'strong_positive',     # 0.30-0.40
    ('pitcher_hits_allowed', 'batter_rbis'): 'moderate_positive',      # 0.30-0.40
    ('hits_allowed', 'hits'): 'strong_positive',                       # 0.35-0.45
    ('hits_allowed', 'total_bases'): 'moderate_positive',              # 0.25-0.35
    ('hits_allowed', 'singles'): 'strong_positive',                    # 0.30-0.40
    ('hits_allowed', 'rbis'): 'moderate_positive',                     # 0.30-0.40
    ('allowed_hits', 'hits'): 'strong_positive',                       # 0.35-0.45
    ('allowed_hits', 'total_bases'): 'moderate_positive',              # 0.25-0.35
    ('allowed_hits', 'singles'): 'strong_positive',                    # 0.30-0.40
    ('allowed_hits', 'rbis'): 'moderate_positive',                     # 0.30-0.40
    
    # PITCHER OUTS CORRELATIONS
    ('pitcher_outs', 'batter_outs'): 'moderate_positive',              # Direct relationship
    ('outs', 'outs'): 'moderate_positive',                             # Direct relationship
    ('total_outs', 'outs'): 'moderate_positive',                       # Direct relationship
    
    # SAME TEAM BATTER CORRELATIONS (for 3+ leg parlays)
    ('batter_hits', 'batter_runs_scored'): 'moderate_positive',        # 0.25-0.35 (same team)
    ('batter_hits', 'batter_rbis'): 'moderate_positive',               # 0.25-0.35 (same team)
    ('hits', 'runs'): 'moderate_positive',                             # 0.25-0.35 (same team)
    ('hits', 'rbis'): 'moderate_positive',                             # 0.25-0.35 (same team)
}

def get_correlation_score(anchor_prop, batter_prop):
    """
    Get correlation score between pitcher anchor and batter prop
    
    Args:
        anchor_prop: Dict with keys: market, ou, player_name, team
        batter_prop: Dict with keys: market, ou, player_name, team  
        
    Returns:
        Decimal: Correlation score
    """
    # Check if same game
    if not _is_same_game(anchor_prop, batter_prop):
        return CORRELATION_VALUES['independent']
    
    # Check if opposing teams (for pitcher vs batter correlations)
    opposing_teams = _are_opposing_teams(anchor_prop, batter_prop)
    
    # Get base correlation from matrix
    correlation_key = (anchor_prop['market'], batter_prop['market'])
    
    if correlation_key in MLB_CORRELATIONS:
        base_correlation = CORRELATION_VALUES[MLB_CORRELATIONS[correlation_key]]
        
        # Apply direction rules
        if base_correlation > 0:  # Positive correlation
            # Same direction (both over or both under)
            if anchor_prop['ou'] == batter_prop['ou']:
                return base_correlation
            else:
                return CORRELATION_VALUES['independent']
        else:  # Negative correlation
            # Opposite direction (over vs under)
            if anchor_prop['ou'] != batter_prop['ou']:
                return abs(base_correlation) * Decimal('-1')
            else:
                return CORRELATION_VALUES['independent']
    
    return CORRELATION_VALUES['independent']

def get_correlated_markets(anchor_market, correlation_type='all'):
    """
    Get all markets that correlate with the anchor market
    
    Args:
        anchor_market: The pitcher's market (e.g., 'pitcher_strikeouts')
        correlation_type: 'positive', 'negative', or 'all'
        
    Returns:
        List of tuples: [(market, correlation_strength, correlation_type)]
    """
    correlated_markets = []
    
    for (pitcher_market, batter_market), corr_type in MLB_CORRELATIONS.items():
        if pitcher_market == anchor_market:
            corr_value = CORRELATION_VALUES[corr_type]
            
            if correlation_type == 'all':
                correlated_markets.append((batter_market, corr_value, corr_type))
            elif correlation_type == 'positive' and corr_value > 0:
                correlated_markets.append((batter_market, corr_value, corr_type))
            elif correlation_type == 'negative' and corr_value < 0:
                correlated_markets.append((batter_market, corr_value, corr_type))
    
    # Sort by absolute correlation strength
    correlated_markets.sort(key=lambda x: abs(x[1]), reverse=True)
    
    return correlated_markets

def _is_same_game(prop1, prop2):
    """Check if two props are from the same game"""
    return (prop1.get('home') == prop2.get('home') and 
            prop1.get('away') == prop2.get('away'))

def _are_opposing_teams(prop1, prop2):
    """Check if two props are from opposing teams"""
    # This is simplified - in reality we'd need to know which team each player is on
    # For now, assume pitcher and batter are on opposing teams if in same game
    return (_is_same_game(prop1, prop2) and 
            'pitcher' in prop1['market'] and 
            'batter' in prop2['market'])

def get_correlation_direction(anchor_ou, correlation_type):
    """
    Determine what direction the correlated prop should be
    
    Args:
        anchor_ou: 'O' or 'U' for the anchor prop
        correlation_type: 'positive' or 'negative'
        
    Returns:
        'O' or 'U' for the correlated prop
    """
    if 'positive' in correlation_type:
        # Positive correlation: same direction
        return anchor_ou
    else:
        # Negative correlation: opposite direction  
        return 'U' if anchor_ou == 'O' else 'O'

def format_correlation_display(correlation_value):
    """Format correlation value for display"""
    if correlation_value < -0.25:
        return "Strong Negative"
    elif correlation_value < 0:
        return "Moderate Negative"
    elif correlation_value == 0:
        return "Independent"
    elif correlation_value < 0.35:
        return "Moderate Positive"
    else:
        return "Strong Positive"

# Correlation descriptions for UI
CORRELATION_DESCRIPTIONS = {
    # Pitcher strikeouts correlations
    ('pitcher_strikeouts', 'batter_hits'): "More Ks = Fewer hits",
    ('pitcher_strikeouts', 'batter_total_bases'): "More Ks = Fewer total bases",
    ('pitcher_strikeouts', 'batter_singles'): "More Ks = Fewer singles",
    ('strikeouts', 'hits'): "More Ks = Fewer hits",
    ('strikeouts', 'total_bases'): "More Ks = Fewer total bases",
    ('strikeouts', 'singles'): "More Ks = Fewer singles",
    
    # Pitcher earned runs correlations
    ('pitcher_earned_runs', 'batter_runs_scored'): "More ER = More runs scored",
    ('pitcher_earned_runs', 'batter_rbis'): "More ER = More RBIs",
    ('earned_runs', 'runs'): "More ER = More runs scored",
    ('earned_runs', 'rbis'): "More ER = More RBIs",
    
    # Pitcher hits allowed correlations
    ('pitcher_hits_allowed', 'batter_hits'): "More hits allowed = More hits",
    ('pitcher_hits_allowed', 'batter_total_bases'): "More hits allowed = More bases",
    ('pitcher_hits_allowed', 'batter_singles'): "More hits allowed = More singles",
    ('pitcher_hits_allowed', 'batter_rbis'): "More hits allowed = More RBIs",
    ('hits_allowed', 'hits'): "More hits allowed = More hits",
    ('hits_allowed', 'total_bases'): "More hits allowed = More bases",
    ('hits_allowed', 'singles'): "More hits allowed = More singles",
    ('hits_allowed', 'rbis'): "More hits allowed = More RBIs",
    ('allowed_hits', 'hits'): "More hits allowed = More hits",
    ('allowed_hits', 'total_bases'): "More hits allowed = More bases",
    ('allowed_hits', 'singles'): "More hits allowed = More singles",
    ('allowed_hits', 'rbis'): "More hits allowed = More RBIs",
}