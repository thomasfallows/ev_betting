"""
Smart parlay generator with correlation detection
"""

import itertools
import logging
from decimal import Decimal
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config'))
from contest_config import CONTEST_CONFIGS, calculate_contest_ev
from correlation_rules import get_correlation_score, get_correlation_description, calculate_variance_reduction

class ParlayGenerator:
    def __init__(self, props, contest_type='2-man', bankroll=60):
        self.props = props
        self.contest_type = contest_type
        self.config = CONTEST_CONFIGS[contest_type]
        self.required_legs = self.config['parlay_legs']
        self.bankroll = bankroll
        
    def calculate_parlay_metrics(self, legs):
        """Calculate comprehensive metrics for a parlay"""
        # Calculate base parlay probability
        parlay_prob = Decimal(1)
        for leg in legs:
            parlay_prob *= Decimal(str(leg['true_probability']))
        
        # Get EV calculation
        ev_result = calculate_contest_ev(float(parlay_prob), self.contest_type)
        
        # Calculate correlation scores for all leg pairs
        correlation_scores = []
        for i in range(len(legs)):
            for j in range(i+1, len(legs)):
                score = get_correlation_score(legs[i], legs[j], legs[0].get('sport', 'mlb'))
                correlation_scores.append(score)
        
        # Average correlation
        avg_correlation = sum(correlation_scores) / len(correlation_scores) if correlation_scores else Decimal(0)
        
        # Variance reduction
        variance_multiplier = calculate_variance_reduction(avg_correlation)
        
        # Confidence based on book count
        avg_books = sum(leg.get('book_count', 1) for leg in legs) / len(legs)
        confidence = min(avg_books / 5, 1.0)  # Max confidence at 5+ books
        
        # Risk-adjusted score (higher is better)
        # Base EV adjusted for variance and confidence
        risk_adjusted_score = (
            ev_result['contest_ev_percent'] * confidence * (2 - variance_multiplier)
        )
        
        return {
            'parlay_probability': float(parlay_prob),
            'ev_result': ev_result,
            'correlation_scores': [float(s) for s in correlation_scores],
            'avg_correlation': float(avg_correlation),
            'correlation_desc': get_correlation_description(avg_correlation),
            'variance_multiplier': variance_multiplier,
            'confidence': confidence,
            'risk_adjusted_score': risk_adjusted_score,
            'kelly_fraction': self._calculate_kelly(ev_result, variance_multiplier)
        }
    
    def _calculate_kelly(self, ev_result, variance_multiplier):
        """Calculate Kelly fraction with variance adjustment"""
        if ev_result['edge_over_breakeven'] <= 0:
            return 0
        
        # Standard Kelly: f = edge / odds
        # For 2-man: odds = 2 (net profit of 2x on win)
        odds = self.config['payout_multiple'] - 1
        kelly = ev_result['edge_over_breakeven'] / odds
        
        # Adjust for variance (less aggressive with higher variance)
        adjusted_kelly = kelly / variance_multiplier
        
        # Apply fractional Kelly (1/4 for safety)
        return adjusted_kelly * 0.25
    
    def _are_same_game(self, leg1, leg2):
        """Check if two legs are from the same game"""
        return (leg1['home'] == leg2['home'] and leg1['away'] == leg2['away'])
    
    def _are_same_player(self, leg1, leg2):
        """Check if two legs are for the same player"""
        return leg1.get('player_name') == leg2.get('player_name')
    
    def generate_smart_parlays(self, max_results=50):
        """Generate parlays with intelligent filtering and ranking"""
        logger.info(f"[Parlay Gen] Starting smart parlay generation for {self.contest_type}")
        logger.info(f"[Parlay Gen] Available props: {len(self.props)}")
        
        # Pre-filter props by minimum probability - lower threshold to show more
        min_prob = 0.50  # Show parlays with 50%+ per leg probability
        viable_props = [p for p in self.props if p['true_probability'] >= min_prob]
        logger.info(f"[Parlay Gen] Viable props (>={min_prob:.1%}): {len(viable_props)}")
        
        if len(viable_props) < self.required_legs:
            logger.warning(f"[Parlay Gen] Not enough viable props for {self.required_legs}-leg parlays")
            return []
        
        # Group props by game
        games = {}
        for prop in viable_props:
            game_key = (prop['home'], prop['away'])
            if game_key not in games:
                games[game_key] = []
            games[game_key].append(prop)
        
        all_parlays = []
        
        # Strategy 1: Find negatively correlated parlays within same game
        logger.info("[Parlay Gen] Searching for correlated parlays...")
        for game_key, game_props in games.items():
            if len(game_props) >= self.required_legs:
                # Try small samples first
                for combo in itertools.combinations(game_props[:10], self.required_legs):
                    if self._is_valid_parlay(combo):
                        metrics = self.calculate_parlay_metrics(combo)
                        if metrics['avg_correlation'] < 0:  # Just check for negative correlation
                            all_parlays.append({
                                'legs': combo,
                                'metrics': metrics,
                                'type': 'correlated',
                                'game': game_key
                            })
        
        logger.info(f"[Parlay Gen] Found {len(all_parlays)} correlated parlays")
        
        # Strategy 2: High-probability independent parlays (different games)
        if len(all_parlays) < max_results:
            logger.info("[Parlay Gen] Searching for independent parlays...")
            
            # Sort by probability for best candidates
            sorted_props = sorted(viable_props, key=lambda x: x['true_probability'], reverse=True)
            
            # Take top props from different games
            independent_candidates = []
            seen_games = set()
            for prop in sorted_props:
                game_key = (prop['home'], prop['away'])
                if game_key not in seen_games:
                    independent_candidates.append(prop)
                    seen_games.add(game_key)
                if len(independent_candidates) >= 20:  # Limit search space
                    break
            
            # Generate combinations
            if len(independent_candidates) >= self.required_legs:
                for combo in itertools.combinations(independent_candidates, self.required_legs):
                    if self._is_valid_parlay(combo):
                        metrics = self.calculate_parlay_metrics(combo)
                        # Add all parlays regardless of EV
                        all_parlays.append({
                            'legs': combo,
                            'metrics': metrics,
                            'type': 'independent',
                            'game': 'multiple'
                        })
                        
                        if len(all_parlays) >= max_results * 2:  # Generate extra to filter
                            break
        
        logger.info(f"[Parlay Gen] Total parlays found: {len(all_parlays)}")
        
        # Sort by risk-adjusted score
        all_parlays.sort(key=lambda x: x['metrics']['risk_adjusted_score'], reverse=True)
        
        # Return all parlays without Kelly filtering to show all options
        logger.info(f"[Parlay Gen] Returning all {len(all_parlays)} parlays")
        
        return all_parlays[:max_results]
    
    def _is_valid_parlay(self, legs):
        """Check if a parlay combination is valid"""
        # No duplicate players
        players = [leg['player_name'] for leg in legs]
        if len(players) != len(set(players)):
            return False
        
        # Additional sport-specific rules can be added here
        
        return True
    
    def format_parlay_summary(self, parlay):
        """Format a parlay for display"""
        metrics = parlay['metrics']
        lines = [
            f"{'='*60}",
            f"{parlay['type'].upper()} PARLAY - {self.contest_type}",
            f"{'='*60}",
            f"Parlay Probability: {metrics['parlay_probability']*100:.2f}%",
            f"Contest EV: {metrics['ev_result']['contest_ev_percent']:.2f}%",
            f"Edge over break-even: {metrics['ev_result']['edge_over_breakeven']*100:.2f}%",
            f"Correlation: {metrics['correlation_desc']} ({metrics['avg_correlation']:.2f})",
            f"Variance Multiplier: {metrics['variance_multiplier']:.2f}x",
            f"Confidence: {metrics['confidence']*100:.0f}%",
            f"Risk-Adjusted Score: {metrics['risk_adjusted_score']:.2f}",
            f"Kelly Bet Size: {metrics['kelly_fraction']*100:.1f}% of bankroll (${self.bankroll * metrics['kelly_fraction']:.2f})",
            f"\nLegs:"
        ]
        
        for i, leg in enumerate(parlay['legs'], 1):
            lines.append(
                f"{i}. {leg['player_name']} ({leg['sport'].upper()}) "
                f"{leg['market']} {leg['ou']} {leg['line']} "
                f"- Prob: {leg['true_probability']*100:.1f}%"
            )
        
        return '\n'.join(lines)


def demo_parlay_generation():
    """Demo function to show parlay generation"""
    # Sample props for testing
    sample_props = [
        {
            'player_name': 'Gerrit Cole',
            'normalized_name': 'gerrit_cole',
            'market': 'pitcher_strikeouts',
            'line': 7.5,
            'ou': 'O',
            'true_probability': 0.62,
            'home': 'Yankees',
            'away': 'Red Sox',
            'sport': 'mlb',
            'book_count': 5
        },
        {
            'player_name': 'Rafael Devers',
            'normalized_name': 'rafael_devers',
            'market': 'batter_hits',
            'line': 1.5,
            'ou': 'U',
            'true_probability': 0.59,
            'home': 'Yankees', 
            'away': 'Red Sox',
            'sport': 'mlb',
            'book_count': 4
        },
        {
            'player_name': 'Aaron Judge',
            'normalized_name': 'aaron_judge',
            'market': 'batter_total_bases',
            'line': 2.5,
            'ou': 'O',
            'true_probability': 0.58,
            'home': 'Yankees',
            'away': 'Red Sox', 
            'sport': 'mlb',
            'book_count': 3
        }
    ]
    
    generator = ParlayGenerator(sample_props, '2-man')
    parlays = generator.generate_smart_parlays(max_results=5)
    
    print(f"\nFound {len(parlays)} parlays:")
    for parlay in parlays:
        print(generator.format_parlay_summary(parlay))
        print()


if __name__ == "__main__":
    demo_parlay_generation()