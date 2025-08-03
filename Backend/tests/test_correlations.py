"""
Test correlation detection and parlay generation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config'))

from correlation_rules import get_correlation_score, get_correlation_description
from data_scripts.parlay_generator import ParlayGenerator
from decimal import Decimal

def test_correlation_detection():
    """Test various correlation scenarios"""
    print("Testing Correlation Detection\n" + "="*50)
    
    # Test 1: Strong negative correlation (pitcher K vs hits)
    leg1 = {
        'player_name': 'Gerrit Cole',
        'market': 'pitcher_strikeouts',
        'ou': 'O',
        'home': 'Yankees',
        'away': 'Red Sox',
        'sport': 'mlb'
    }
    leg2 = {
        'player_name': 'Rafael Devers',
        'market': 'batter_hits',
        'ou': 'O',
        'home': 'Yankees',
        'away': 'Red Sox',
        'sport': 'mlb'
    }
    
    score = get_correlation_score(leg1, leg2, 'mlb')
    print(f"Test 1 - Pitcher K (O) vs Batter Hits (O):")
    print(f"  Score: {score}")
    print(f"  Description: {get_correlation_description(score)}")
    print(f"  Expected: Strong negative correlation [PASS]\n" if score < -0.5 else "  FAILED!\n")
    
    # Test 2: Strong positive correlation (same player hits/TB)
    leg3 = {
        'player_name': 'Aaron Judge',
        'market': 'batter_hits',
        'ou': 'O',
        'home': 'Yankees',
        'away': 'Red Sox',
        'sport': 'mlb'
    }
    leg4 = {
        'player_name': 'Aaron Judge',
        'market': 'batter_total_bases',
        'ou': 'O',
        'home': 'Yankees',
        'away': 'Red Sox',
        'sport': 'mlb'
    }
    
    score2 = get_correlation_score(leg3, leg4, 'mlb')
    print(f"Test 2 - Same player Hits (O) vs Total Bases (O):")
    print(f"  Score: {score2}")
    print(f"  Description: {get_correlation_description(score2)}")
    print(f"  Expected: Strong positive correlation [PASS]\n" if score2 > 0.5 else "  FAILED!\n")
    
    # Test 3: Independent (different games)
    leg5 = {
        'player_name': 'Mike Trout',
        'market': 'batter_hits',
        'ou': 'O',
        'home': 'Angels',
        'away': 'Astros',
        'sport': 'mlb'
    }
    
    score3 = get_correlation_score(leg3, leg5, 'mlb')
    print(f"Test 3 - Different games:")
    print(f"  Score: {score3}")
    print(f"  Description: {get_correlation_description(score3)}")
    print(f"  Expected: Independent [PASS]\n" if score3 == 0 else "  FAILED!\n")

def test_parlay_generation_with_correlations():
    """Test parlay generation with good data"""
    print("\nTesting Parlay Generation with Correlations\n" + "="*50)
    
    # Create props that will generate valid parlays
    props = [
        # Correlated pair in same game
        {
            'player_name': 'Shane Bieber',
            'normalized_name': 'shane_bieber',
            'market': 'pitcher_strikeouts',
            'line': 8.5,
            'ou': 'O',
            'true_probability': 0.65,  # Strong probability
            'home': 'Guardians',
            'away': 'Twins',
            'sport': 'mlb',
            'book_count': 5
        },
        {
            'player_name': 'Carlos Correa',
            'normalized_name': 'carlos_correa',
            'market': 'batter_hits',
            'line': 1.5,
            'ou': 'U',  # Under hits when pitcher has high Ks
            'true_probability': 0.63,
            'home': 'Guardians',
            'away': 'Twins',
            'sport': 'mlb',
            'book_count': 4
        },
        # Another game for independent parlay
        {
            'player_name': 'Shohei Ohtani',
            'normalized_name': 'shohei_ohtani',
            'market': 'batter_total_bases',
            'line': 2.5,
            'ou': 'O',
            'true_probability': 0.62,
            'home': 'Dodgers',
            'away': 'Giants',
            'sport': 'mlb',
            'book_count': 6
        },
        # WNBA example
        {
            'player_name': 'Arike Ogunbowale',
            'normalized_name': 'arike_ogunbowale',
            'market': 'player_points',
            'line': 22.5,
            'ou': 'U',
            'true_probability': 0.61,
            'home': 'Wings',
            'away': 'Storm',
            'sport': 'wnba',
            'book_count': 3
        },
        {
            'player_name': 'Arike Ogunbowale',
            'normalized_name': 'arike_ogunbowale',
            'market': 'player_assists',
            'line': 5.5,
            'ou': 'O',
            'true_probability': 0.60,
            'home': 'Wings',
            'away': 'Storm',
            'sport': 'wnba',
            'book_count': 3
        }
    ]
    
    # Test 2-man parlays
    generator = ParlayGenerator(props, '2-man', bankroll=60)
    parlays = generator.generate_smart_parlays(max_results=10)
    
    print(f"Generated {len(parlays)} valid 2-man parlays\n")
    
    # Show top 3
    for i, parlay in enumerate(parlays[:3], 1):
        print(f"\nParlay #{i}:")
        print(generator.format_parlay_summary(parlay))
        print("\n" + "-"*60)

def test_correlation_matrix():
    """Test correlation matrix for multiple props"""
    print("\nTesting Correlation Matrix\n" + "="*50)
    
    props = [
        {'player_name': 'P1', 'market': 'pitcher_strikeouts', 'ou': 'O', 'home': 'A', 'away': 'B'},
        {'player_name': 'P2', 'market': 'batter_hits', 'ou': 'O', 'home': 'A', 'away': 'B'},
        {'player_name': 'P3', 'market': 'batter_hits', 'ou': 'U', 'home': 'A', 'away': 'B'},
        {'player_name': 'P4', 'market': 'pitcher_earned_runs', 'ou': 'U', 'home': 'A', 'away': 'B'},
    ]
    
    print("Correlation Matrix:")
    print("       ", end="")
    for i, p in enumerate(props):
        print(f"  P{i+1}  ", end="")
    print()
    
    for i, p1 in enumerate(props):
        print(f"P{i+1}     ", end="")
        for j, p2 in enumerate(props):
            if i == j:
                print(" 1.00 ", end="")
            else:
                score = get_correlation_score(p1, p2, 'mlb')
                print(f"{score:6.2f}", end="")
        print()
    
    print("\nLegend:")
    print("P1: Pitcher Strikeouts O")
    print("P2: Batter Hits O (opposing team)")
    print("P3: Batter Hits U (opposing team)")
    print("P4: Pitcher Earned Runs U")

if __name__ == "__main__":
    test_correlation_detection()
    test_parlay_generation_with_correlations()
    test_correlation_matrix()