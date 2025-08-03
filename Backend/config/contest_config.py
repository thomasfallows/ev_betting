"""
Contest configuration for Splash Sports
Contains break-even probabilities and payout structures for each contest type
"""

from decimal import Decimal

CONTEST_CONFIGS = {
    '2-man': {
        'lobby_size': 4,
        'payout_multiple': 3,
        'rake_percent': 25.0,
        'break_even_prob': Decimal(1) / Decimal(3),  # 33.33%
        'min_edge_required': Decimal('0.07'),  # Need 40%+ for safety with small bankroll
        'parlay_legs': 2,
        'per_leg_breakeven': Decimal('0.5774')  # sqrt(1/3)
    },
    '3-man': {
        'lobby_size': 8,
        'payout_multiple': 6,
        'rake_percent': 25.0,
        'break_even_prob': Decimal(1) / Decimal(6),  # 16.67%
        'min_edge_required': Decimal('0.04'),  # Need 20%+
        'parlay_legs': 3,
        'per_leg_breakeven': Decimal('0.5504')  # (1/6)^(1/3)
    },
    '4-man': {
        'lobby_size': 16,
        'payout_multiple': 12,
        'rake_percent': 25.0,
        'break_even_prob': Decimal(1) / Decimal(12),  # 8.33%
        'min_edge_required': Decimal('0.02'),
        'parlay_legs': 4,
        'per_leg_breakeven': Decimal('0.5313')  # (1/12)^(1/4)
    },
    '5-man': {
        'lobby_size': 32,
        'payout_multiple': 25,
        'rake_percent': 21.8,
        'break_even_prob': Decimal(1) / Decimal(25),  # 4%
        'min_edge_required': Decimal('0.01'),
        'parlay_legs': 5,
        'per_leg_breakeven': Decimal('0.5119')  # (1/25)^(1/5)
    },
    '6-man': {
        'lobby_size': 64,
        'payout_multiple': 50,
        'rake_percent': 21.8,
        'break_even_prob': Decimal(1) / Decimal(50),  # 2%
        'min_edge_required': Decimal('0.005'),
        'parlay_legs': 6,
        'per_leg_breakeven': Decimal('0.4929')  # (1/50)^(1/6)
    }
}

def calculate_contest_ev(parlay_probability, contest_type='2-man'):
    """
    Calculate true EV for a contest
    
    Args:
        parlay_probability: Decimal probability of winning the parlay (0-1)
        contest_type: Type of contest ('2-man', '3-man', etc.)
    
    Returns:
        dict with EV metrics
    """
    config = CONTEST_CONFIGS[contest_type]
    
    # Convert to Decimal for consistent calculation
    parlay_prob_decimal = Decimal(str(parlay_probability))
    
    # EV = (P × (Payout - 1)) - (1 - P)
    # Simplified: EV = P × Payout - 1
    win_amount = config['payout_multiple'] - 1
    ev = (parlay_prob_decimal * win_amount) - (1 - parlay_prob_decimal)
    ev_percent = ev * 100
    
    # Calculate edge over break-even
    edge = parlay_prob_decimal - config['break_even_prob']
    
    return {
        'parlay_probability': float(parlay_prob_decimal),
        'contest_ev_percent': float(ev_percent),
        'break_even_probability': float(config['break_even_prob']),
        'edge_over_breakeven': float(edge),
        'expected_roi': float(ev),
        'should_bet': edge > config['min_edge_required'],
        'meets_minimum': parlay_prob_decimal > (config['break_even_prob'] + config['min_edge_required'])
    }

# Bankroll recommendations based on contest type and bankroll size
BANKROLL_RECOMMENDATIONS = {
    'micro': {  # < $100
        'bankroll_range': (0, 100),
        'recommended_contests': ['2-man'],
        'max_daily_risk': 0.25,  # 25% of bankroll
        'kelly_fraction': 0.25   # 1/4 Kelly
    },
    'small': {  # $100-$500
        'bankroll_range': (100, 500),
        'recommended_contests': ['2-man', '3-man'],
        'max_daily_risk': 0.20,
        'kelly_fraction': 0.33
    },
    'medium': {  # $500-$2000
        'bankroll_range': (500, 2000),
        'recommended_contests': ['2-man', '3-man', '4-man'],
        'max_daily_risk': 0.15,
        'kelly_fraction': 0.5
    },
    'large': {  # $2000+
        'bankroll_range': (2000, float('inf')),
        'recommended_contests': ['2-man', '3-man', '4-man', '5-man', '6-man'],
        'max_daily_risk': 0.10,
        'kelly_fraction': 0.75
    }
}

def get_bankroll_recommendation(bankroll_size):
    """Get contest recommendations based on bankroll size"""
    for category, config in BANKROLL_RECOMMENDATIONS.items():
        if config['bankroll_range'][0] <= bankroll_size < config['bankroll_range'][1]:
            return config
    return BANKROLL_RECOMMENDATIONS['large']  # Default for very large bankrolls