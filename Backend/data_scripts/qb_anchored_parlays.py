"""
QB-Anchored Parlay Generator for NFL/NCAAF
Focuses on correlation-based parlay construction with QBs as anchors
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

from football_correlation_rules import (
    get_correlated_markets,
    get_correlation_score,
    get_correlation_type,
    format_correlation_display,
    get_correlation_description
)

class QBAnchoredParlayGenerator:
    def __init__(self, all_props, sport='nfl'):
        """
        Initialize with all available props

        Args:
            all_props: List of dicts with keys:
                - player_name, normalized_name, market, line, ou
                - true_probability, ev_percentage, home, away, sport, team
                - position_football (QB, WR1, WR2, WR3, TE, RB)
            sport: 'nfl' or 'ncaaf'
        """
        self.all_props = all_props
        self.sport = sport
        self._organize_props()

    def _organize_props(self):
        """Organize props by game and type"""
        self.games = defaultdict(lambda: {'qbs': [], 'receivers': []})

        # Define QB markets
        qb_markets = ['player_pass_yds', 'player_pass_completions']

        # Define receiver markets
        receiver_markets = ['player_reception_yds', 'player_receptions']

        for prop in self.all_props:
            # Filter to correct sport
            if prop.get('sport') != self.sport:
                continue

            game_key = (prop['home'], prop['away'])

            # Check if QB prop
            if prop['market'] in qb_markets and prop.get('position_football') == 'QB':
                self.games[game_key]['qbs'].append(prop)
            # Check if receiver prop
            elif prop['market'] in receiver_markets and prop.get('position_football') in ['WR1', 'WR2', 'WR3', 'TE', 'RB']:
                self.games[game_key]['receivers'].append(prop)

    def find_qb_anchors(self, min_ev=None):
        """
        Find all QB props that can serve as anchors

        Returns:
            Dict: {
                'yards': [list of QB pass yards props],
                'completions': [list of QB pass completions props]
            }
        """
        anchors_by_type = {
            'yards': [],
            'completions': []
        }

        for game_key, game_props in self.games.items():
            for qb_prop in game_props['qbs']:
                correlation_type = get_correlation_type(qb_prop['market'])

                if correlation_type != 'unknown':
                    anchors_by_type[correlation_type].append({
                        'prop': qb_prop,
                        'game_key': game_key,
                        'ev': qb_prop.get('ev_percentage', 0)
                    })

        # Sort each type by EV descending
        for corr_type in anchors_by_type:
            anchors_by_type[corr_type].sort(key=lambda x: x['ev'], reverse=True)

        return anchors_by_type

    def get_correlated_receivers(self, qb_prop, game_key):
        """
        Get all correlated receiver props for a given QB anchor

        Returns:
            List of dicts with receiver props and correlation info
        """
        correlated_receivers = []

        # Get all receivers from this game
        game_receivers = self.games[game_key]['receivers']

        # Determine which receiver market is correlated
        correlated_markets_dict = get_correlated_markets(qb_prop['market'])

        for receiver in game_receivers:
            # Check if this receiver's market is correlated
            if receiver['market'] in correlated_markets_dict:
                position = receiver.get('position_football')
                if position and position in correlated_markets_dict[receiver['market']]:
                    # Calculate correlation score
                    correlation_score = get_correlation_score(qb_prop, receiver)

                    if correlation_score > 0:
                        # Check if same direction (both Over or both Under)
                        if qb_prop['ou'] == receiver['ou']:
                            correlated_receivers.append({
                                'prop': receiver,
                                'correlation_score': float(correlation_score),
                                'correlation_description': get_correlation_description(qb_prop, receiver),
                                'ev': receiver.get('ev_percentage', 0),
                                'position': position
                            })

        # Sort by EV descending
        correlated_receivers.sort(key=lambda x: x['ev'], reverse=True)

        return correlated_receivers

    def generate_stacks_by_type(self, limit=None):
        """
        Generate QB-anchored stacks grouped by correlation type (yards, completions)

        Returns:
            Dict: {
                'yards': [list of stacks],
                'completions': [list of stacks]
            }
        """
        stacks_by_type = {
            'yards': [],
            'completions': []
        }

        # Get all QB anchors by type
        anchors_by_type = self.find_qb_anchors()

        for corr_type, anchors in anchors_by_type.items():
            # Apply limit if specified
            if limit:
                anchors = anchors[:limit]

            for anchor_data in anchors:
                qb_prop = anchor_data['prop']
                game_key = anchor_data['game_key']

                # Get correlated receivers
                receivers = self.get_correlated_receivers(qb_prop, game_key)

                # Only create stack if there are correlated receivers
                if receivers:
                    stack = {
                        'qb': {
                            'player_name': qb_prop['player_name'],
                            'market': qb_prop['market'],
                            'line': qb_prop['line'],
                            'ou': qb_prop['ou'],
                            'ev': qb_prop.get('ev_percentage', 0),
                            'home': qb_prop['home'],
                            'away': qb_prop['away'],
                            'book_count': qb_prop.get('book_count', 0),
                            'true_probability': qb_prop.get('true_probability', 0)
                        },
                        'receivers': [],
                        'correlation_type': corr_type
                    }

                    # Add all correlated receivers
                    for receiver_data in receivers:
                        receiver_prop = receiver_data['prop']
                        stack['receivers'].append({
                            'player_name': receiver_prop['player_name'],
                            'market': receiver_prop['market'],
                            'line': receiver_prop['line'],
                            'ou': receiver_prop['ou'],
                            'ev': receiver_data['ev'],
                            'position': receiver_data['position'],
                            'correlation_score': receiver_data['correlation_score'],
                            'correlation_description': receiver_data['correlation_description'],
                            'book_count': receiver_prop.get('book_count', 0),
                            'true_probability': receiver_prop.get('true_probability', 0)
                        })

                    stacks_by_type[corr_type].append(stack)

        return stacks_by_type

    def generate_display_data(self, limit=10):
        """
        Generate data structure for frontend display

        Returns:
            Dict: {
                'sport': 'nfl' or 'ncaaf',
                'yards_stacks': [list of stacks],
                'completions_stacks': [list of stacks]
            }
        """
        stacks = self.generate_stacks_by_type(limit=limit)

        return {
            'sport': self.sport,
            'yards_stacks': stacks['yards'],
            'completions_stacks': stacks['completions']
        }


def demo_qb_anchored_parlays():
    """Demo the QB-anchored parlay system"""
    # Sample data
    sample_props = [
        # QB
        {
            'player_name': 'Patrick Mahomes',
            'normalized_name': 'patrick_mahomes',
            'market': 'player_pass_yds',
            'line': 285.5,
            'ou': 'O',
            'true_probability': 0.58,
            'ev_percentage': 3.1,
            'home': 'Chiefs',
            'away': 'Broncos',
            'sport': 'nfl',
            'team': 'Chiefs',
            'position_football': 'QB',
            'book_count': 8
        },
        # WR1
        {
            'player_name': 'Travis Kelce',
            'normalized_name': 'travis_kelce',
            'market': 'player_reception_yds',
            'line': 65.5,
            'ou': 'O',
            'true_probability': 0.59,
            'ev_percentage': 1.2,
            'home': 'Chiefs',
            'away': 'Broncos',
            'sport': 'nfl',
            'team': 'Chiefs',
            'position_football': 'TE',
            'book_count': 5
        },
        # WR2
        {
            'player_name': 'Tyreek Hill',
            'normalized_name': 'tyreek_hill',
            'market': 'player_reception_yds',
            'line': 85.5,
            'ou': 'O',
            'true_probability': 0.57,
            'ev_percentage': -0.5,
            'home': 'Chiefs',
            'away': 'Broncos',
            'sport': 'nfl',
            'team': 'Chiefs',
            'position_football': 'WR1',
            'book_count': 6
        }
    ]

    generator = QBAnchoredParlayGenerator(sample_props, sport='nfl')
    display_data = generator.generate_display_data()

    print("QB-ANCHORED PARLAY DISPLAY (NFL)")
    print("=" * 80)

    print("\n=== YARDS CORRELATIONS ===")
    for stack in display_data['yards_stacks']:
        qb = stack['qb']
        print(f"\nQB: {qb['player_name']} - {qb['market']} {qb['ou']} {qb['line']} ({qb['ev']:+.1f}% EV)")
        print(f"Game: {qb['away']} @ {qb['home']}")
        print("-" * 80)

        print("Correlated Receivers:")
        for receiver in stack['receivers']:
            print(f"  {receiver['player_name']} ({receiver['position']}) - {receiver['market']} {receiver['ou']} {receiver['line']}")
            print(f"    EV: {receiver['ev']:+.1f}% | Correlation: {receiver['correlation_score']:.2f} | Books: {receiver['book_count']}")

    print("\n=== COMPLETIONS CORRELATIONS ===")
    for stack in display_data['completions_stacks']:
        qb = stack['qb']
        print(f"\nQB: {qb['player_name']} - {qb['market']} {qb['ou']} {qb['line']} ({qb['ev']:+.1f}% EV)")
        print(f"Game: {qb['away']} @ {qb['home']}")
        print("-" * 80)

        print("Correlated Receivers:")
        for receiver in stack['receivers']:
            print(f"  {receiver['player_name']} ({receiver['position']}) - {receiver['market']} {receiver['ou']} {receiver['line']}")
            print(f"    EV: {receiver['ev']:+.1f}% | Correlation: {receiver['correlation_score']:.2f} | Books: {receiver['book_count']}")


if __name__ == "__main__":
    demo_qb_anchored_parlays()
