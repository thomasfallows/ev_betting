"""
Pitcher-Anchored Parlay Generator
Focuses on correlation-based parlay construction with pitchers as anchors
"""

import logging
from decimal import Decimal
from collections import defaultdict
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config'))

from correlation_rules import (
    get_correlated_markets, 
    get_correlation_direction,
    get_correlation_score,
    format_correlation_display,
    CORRELATION_DESCRIPTIONS
)

class PitcherAnchoredParlayGenerator:
    def __init__(self, all_props):
        """
        Initialize with all available props
        
        Args:
            all_props: List of dicts with keys:
                - player_name, normalized_name, market, line, ou
                - true_probability, ev_percentage, home, away, sport, team
        """
        self.all_props = all_props
        self._organize_props()
        
    def _organize_props(self):
        """Organize props by game and type"""
        self.games = defaultdict(lambda: {'pitchers': [], 'batters': []})
        
        # Define pitcher markets
        pitcher_markets = ['strikeouts', 'earned_runs', 'allowed_hits', 'hits_allowed', 'outs', 'total_outs',
                          'pitcher_strikeouts', 'pitcher_earned_runs', 'pitcher_hits_allowed', 'pitcher_outs']
        
        for prop in self.all_props:
            game_key = (prop['home'], prop['away'])
            
            if prop['market'] in pitcher_markets or 'pitcher' in prop['market']:
                self.games[game_key]['pitchers'].append(prop)
            elif 'batter' in prop['market'] or prop['market'] in ['hits', 'singles', 'runs', 'rbis', 'total_bases']:
                self.games[game_key]['batters'].append(prop)
                
    def find_pitcher_anchors(self, min_ev=None):
        """
        Find all pitcher props that can serve as anchors
        Prioritize Earned Runs market
        
        Returns:
            List of anchor props sorted by EV
        """
        anchors = []
        
        for game_key, game_props in self.games.items():
            for pitcher_prop in game_props['pitchers']:
                # For testing: show all pitcher props, not just positive EV
                # Add priority score (ER market gets bonus)
                priority = pitcher_prop.get('ev_percentage', 0)
                if pitcher_prop['market'] == 'pitcher_earned_runs':
                    priority += 10  # Bonus for ER market
                    
                anchors.append({
                    'prop': pitcher_prop,
                    'game_key': game_key,
                    'priority': priority
                })
        
        # Sort by priority (EV + bonus)
        anchors.sort(key=lambda x: x['priority'], reverse=True)
        
        return anchors
    
    def get_correlated_batters(self, anchor_prop, game_key):
        """
        Get all correlated batter props for a given anchor
        
        Returns:
            Dict with correlation sections
        """
        correlations_by_market = defaultdict(list)
        
        # Get all correlated markets for this anchor
        correlated_markets = get_correlated_markets(anchor_prop['market'])
        
        # Get batters from this game
        game_batters = self.games[game_key]['batters']
        
        for batter_market, correlation_value, correlation_type in correlated_markets:
            # Determine required direction for correlation
            required_ou = get_correlation_direction(anchor_prop['ou'], correlation_type)
            
            # Find all batters with this market and direction
            matching_batters = []
            for batter in game_batters:
                if (batter['market'] == batter_market and 
                    batter['ou'] == required_ou):
                    
                    # Calculate actual correlation score
                    correlation_score = get_correlation_score(anchor_prop, batter)
                    
                    matching_batters.append({
                        'prop': batter,
                        'correlation_score': correlation_score,
                        'correlation_type': correlation_type,
                        'ev': batter.get('ev_percentage', 0)
                    })
            
            # Sort by EV within each correlation group
            matching_batters.sort(key=lambda x: x['ev'], reverse=True)
            
            if matching_batters:
                market_key = f"{batter_market}_{required_ou}"
                correlations_by_market[market_key] = {
                    'market': batter_market,
                    'direction': required_ou,
                    'correlation_value': correlation_value,
                    'correlation_type': correlation_type,
                    'batters': matching_batters,
                    'description': CORRELATION_DESCRIPTIONS.get(
                        (anchor_prop['market'], batter_market), 
                        f"{format_correlation_display(correlation_value)} correlation"
                    )
                }
        
        return correlations_by_market
    
    def generate_anchor_display_data(self, limit=None):
        """
        Generate data structure for frontend display
        
        Returns:
            List of anchor sections with correlated batters
        """
        display_data = []
        anchors = self.find_pitcher_anchors()
        
        if limit:
            anchors = anchors[:limit]
            
        for anchor_data in anchors:
            anchor_prop = anchor_data['prop']
            game_key = anchor_data['game_key']
            
            # Get all correlated batters
            correlations = self.get_correlated_batters(anchor_prop, game_key)
            
            # Format for display
            anchor_section = {
                'anchor': {
                    'player_name': anchor_prop['player_name'],
                    'market': anchor_prop['market'],
                    'line': anchor_prop['line'],
                    'ou': anchor_prop['ou'],
                    'ev': anchor_prop.get('ev_percentage', 0),
                    'home': anchor_prop['home'],
                    'away': anchor_prop['away']
                },
                'correlation_sections': []
            }
            
            # Sort correlation sections by strength
            sorted_correlations = sorted(
                correlations.items(), 
                key=lambda x: abs(x[1]['correlation_value']), 
                reverse=True
            )
            
            for market_key, correlation_data in sorted_correlations:
                section = {
                    'market': correlation_data['market'],
                    'direction': correlation_data['direction'],
                    'correlation_value': float(correlation_data['correlation_value']),
                    'correlation_type': correlation_data['correlation_type'],
                    'description': correlation_data['description'],
                    'batters': []
                }
                
                # Add all batters (even negative EV)
                for batter_data in correlation_data['batters']:
                    batter_prop = batter_data['prop']
                    section['batters'].append({
                        'player_name': batter_prop['player_name'],
                        'line': batter_prop['line'],
                        'ev': batter_data['ev'],
                        'true_probability': batter_prop.get('true_probability', 0),
                        'normalized_name': batter_prop['normalized_name']
                    })
                
                anchor_section['correlation_sections'].append(section)
            
            display_data.append(anchor_section)
        
        return display_data
    
    def build_parlay_from_selections(self, anchor_prop, selected_batters):
        """
        Build a valid parlay from user selections
        
        Args:
            anchor_prop: The pitcher anchor prop
            selected_batters: List of selected batter props
            
        Returns:
            Dict with parlay details or error
        """
        # Validate minimum 2 teams
        teams = {anchor_prop.get('team', 'unknown')}
        for batter in selected_batters:
            teams.add(batter.get('team', 'unknown'))
            
        if len(teams) < 2:
            return {'error': 'Parlay must include at least 2 teams'}
        
        # Check for duplicate players
        players = {anchor_prop['player_name']}
        for batter in selected_batters:
            if batter['player_name'] in players:
                return {'error': f'Duplicate player: {batter["player_name"]}'}
            players.add(batter['player_name'])
        
        # Calculate combined probability
        combined_prob = Decimal(str(anchor_prop.get('true_probability', 0.5)))
        for batter in selected_batters:
            combined_prob *= Decimal(str(batter.get('true_probability', 0.5)))
        
        # Build parlay details
        parlay = {
            'legs': [anchor_prop] + selected_batters,
            'combined_probability': float(combined_prob),
            'break_even_probability': 0.5774,  # For 2-man contest
            'expected_value': float(combined_prob) - 0.5774,
            'num_teams': len(teams),
            'correlation_summary': self._get_correlation_summary(anchor_prop, selected_batters)
        }
        
        return parlay
    
    def _get_correlation_summary(self, anchor, batters):
        """Generate correlation summary for parlay"""
        correlations = []
        
        for batter in batters:
            score = get_correlation_score(anchor, batter)
            correlations.append({
                'pair': f"{anchor['player_name']} vs {batter['player_name']}",
                'markets': f"{anchor['market']} vs {batter['market']}",
                'score': float(score),
                'description': format_correlation_display(score)
            })
            
        return correlations


def demo_pitcher_anchored_parlays():
    """Demo the pitcher-anchored parlay system"""
    # Sample data
    sample_props = [
        # Pitchers
        {
            'player_name': 'Gerrit Cole',
            'normalized_name': 'gerrit_cole',
            'market': 'pitcher_strikeouts',
            'line': 7.5,
            'ou': 'O',
            'true_probability': 0.58,
            'ev_percentage': 1.5,
            'home': 'Yankees',
            'away': 'Red Sox',
            'sport': 'mlb',
            'team': 'Yankees'
        },
        {
            'player_name': 'Gerrit Cole',
            'normalized_name': 'gerrit_cole',
            'market': 'pitcher_earned_runs',
            'line': 2.5,
            'ou': 'U',
            'true_probability': 0.55,
            'ev_percentage': -0.5,
            'home': 'Yankees',
            'away': 'Red Sox',
            'sport': 'mlb',
            'team': 'Yankees'
        },
        # Batters - Red Sox
        {
            'player_name': 'Rafael Devers',
            'normalized_name': 'rafael_devers',
            'market': 'batter_hits',
            'line': 1.5,
            'ou': 'U',
            'true_probability': 0.52,
            'ev_percentage': 0.8,
            'home': 'Yankees',
            'away': 'Red Sox',
            'sport': 'mlb',
            'team': 'Red Sox'
        },
        {
            'player_name': 'Rafael Devers',
            'normalized_name': 'rafael_devers',
            'market': 'batter_hits',
            'line': 1.5,
            'ou': 'O',
            'true_probability': 0.48,
            'ev_percentage': -1.2,
            'home': 'Yankees',
            'away': 'Red Sox',
            'sport': 'mlb',
            'team': 'Red Sox'
        },
        {
            'player_name': 'Xander Bogaerts',
            'normalized_name': 'xander_bogaerts',
            'market': 'batter_total_bases',
            'line': 1.5,
            'ou': 'U',
            'true_probability': 0.54,
            'ev_percentage': 0.5,
            'home': 'Yankees',
            'away': 'Red Sox',
            'sport': 'mlb',
            'team': 'Red Sox'
        }
    ]
    
    generator = PitcherAnchoredParlayGenerator(sample_props)
    display_data = generator.generate_anchor_display_data()
    
    print("PITCHER-ANCHORED PARLAY DISPLAY")
    print("=" * 80)
    
    for anchor_section in display_data:
        anchor = anchor_section['anchor']
        print(f"\nANCHOR: {anchor['player_name']} - {anchor['market']} {anchor['ou']} {anchor['line']} ({anchor['ev']:+.1f}% EV)")
        print("-" * 80)
        
        for section in anchor_section['correlation_sections']:
            print(f"\nOPPOSING BATTERS - {section['market'].upper()} {section['direction']} ({section['description']})")
            for i, batter in enumerate(section['batters'], 1):
                print(f"{i}. {batter['player_name']} - {section['market']} {section['direction']} {batter['line']} ({batter['ev']:+.1f}% EV)")


if __name__ == "__main__":
    demo_pitcher_anchored_parlays()