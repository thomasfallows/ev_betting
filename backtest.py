"""
Historical EV Backtesting System
Combines historical Splash picks with Odds API data to test EV strategies
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import json
import time
import os
import pymysql
from typing import Dict, List, Tuple
import itertools
from collections import defaultdict

# Configuration
ODDS_API_KEY = os.environ.get('ODDS_API_KEY', 'YOUR_API_KEY_HERE')
SHARP_BOOKS = ['pinnacle', 'bet365', 'betfair']  # Books to use for true probability

class HistoricalOddsCollector:
    """
    Collects historical odds data from The Odds API
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.session = requests.Session()
        
    def get_historical_odds(self, sport: str, date: str, market: str = 'player_props'):
        """
        Get historical odds for a specific date
        
        Args:
            sport: 'basketball_nba' or 'icehockey_nhl'
            date: Date in YYYY-MM-DD format
            market: Type of market (player_props, etc.)
        """
        # The Odds API historical endpoint (when available)
        url = f"{self.base_url}/historical/sports/{sport}/odds"
        
        params = {
            'apiKey': self.api_key,
            'date': date,
            'markets': market,
            'bookmakers': ','.join(SHARP_BOOKS),
            'oddsFormat': 'american'
        }
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching odds for {date}: {e}")
            return None
    
    def parse_player_props(self, odds_data: Dict) -> List[Dict]:
        """
        Parse player props from API response
        """
        parsed_props = []
        
        if not odds_data:
            return parsed_props
        
        for game in odds_data:
            game_date = game.get('commence_time', '')[:10]
            
            for bookmaker in game.get('bookmakers', []):
                book_name = bookmaker['key']
                
                for market in bookmaker.get('markets', []):
                    if 'player' not in market['key']:
                        continue
                    
                    for outcome in market.get('outcomes', []):
                        prop = {
                            'date': game_date,
                            'game_id': game['id'],
                            'player': outcome.get('description', ''),
                            'market': market['key'],
                            'line': outcome.get('point', 0),
                            'side': outcome['name'],  # over/under
                            'odds': outcome['price'],
                            'bookmaker': book_name
                        }
                        parsed_props.append(prop)
        
        return parsed_props

class EVCalculator:
    """
    Calculate Expected Value using sharp book consensus
    """
    
    @staticmethod
    def american_to_implied_prob(odds: int) -> float:
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    @staticmethod
    def implied_prob_to_american(prob: float) -> int:
        """Convert implied probability to American odds"""
        if prob >= 0.5:
            return -int(prob / (1 - prob) * 100)
        else:
            return int((1 - prob) / prob * 100)
    
    @staticmethod
    def calculate_true_probability(sharp_odds: List[int]) -> float:
        """
        Calculate true probability from sharp book consensus
        Removes vig and averages
        """
        if not sharp_odds:
            return 0.5
        
        # Convert to implied probabilities
        implied_probs = [EVCalculator.american_to_implied_prob(odds) for odds in sharp_odds]
        
        # Simple devig: assume balanced vig and normalize
        avg_prob = np.mean(implied_probs)
        
        # More sophisticated devig could be implemented here
        # For now, simple normalization
        return avg_prob
    
    @staticmethod
    def calculate_ev(true_prob: float, offered_odds: int) -> float:
        """
        Calculate expected value
        
        Args:
            true_prob: True probability (0-1)
            offered_odds: American odds being offered
            
        Returns:
            EV as a percentage
        """
        implied_prob = EVCalculator.american_to_implied_prob(offered_odds)
        
        # EV = (true_prob * payout) - 1
        if offered_odds > 0:
            payout = 1 + (offered_odds / 100)
        else:
            payout = 1 + (100 / abs(offered_odds))
        
        ev = (true_prob * payout) - 1
        return ev * 100  # Return as percentage

class BacktestEngine:
    """
    Run backtests on different strategies
    """
    
    def __init__(self, historical_picks_df: pd.DataFrame, historical_odds_df: pd.DataFrame):
        self.picks = historical_picks_df
        self.odds = historical_odds_df
        self.results = {}
        
    def merge_picks_with_odds(self):
        """
        Match historical picks with odds data
        """
        # Standardize column names for merging
        merge_cols = ['date', 'player', 'market', 'line', 'side']
        
        # Merge picks with odds
        merged = pd.merge(
            self.picks,
            self.odds,
            on=merge_cols,
            how='inner'
        )
        
        return merged
    
    def calculate_all_evs(self, merged_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate EV for all picks
        """
        # Group by pick to get all bookmaker odds
        grouped = merged_df.groupby(['date', 'player', 'market', 'line', 'side'])
        
        ev_results = []
        
        for name, group in grouped:
            # Get sharp book odds
            sharp_odds = group[group['bookmaker'].isin(SHARP_BOOKS)]['odds'].tolist()
            
            if sharp_odds:
                # Calculate true probability
                true_prob = EVCalculator.calculate_true_probability(sharp_odds)
                
                # Calculate EV for each book
                for _, row in group.iterrows():
                    ev = EVCalculator.calculate_ev(true_prob, row['odds'])
                    
                    result = row.to_dict()
                    result['true_probability'] = true_prob
                    result['ev_percentage'] = ev
                    ev_results.append(result)
        
        return pd.DataFrame(ev_results)
    
    def simulate_betting_strategy(self, 
                                ev_df: pd.DataFrame,
                                ev_threshold: float,
                                parlay_size: int,
                                starting_bankroll: float = 1000,
                                bet_size: float = 10) -> Dict:
        """
        Simulate a betting strategy
        
        Args:
            ev_df: DataFrame with EV calculations
            ev_threshold: Minimum EV to place bet (e.g., 5.0 for 5%)
            parlay_size: Number of legs per parlay
            starting_bankroll: Starting amount
            bet_size: Amount per bet
        """
        # Filter for positive EV bets above threshold
        qualifying_bets = ev_df[ev_df['ev_percentage'] >= ev_threshold].copy()
        
        # Group by date
        daily_bets = qualifying_bets.groupby('date')
        
        results = {
            'dates': [],
            'bets_placed': [],
            'bets_won': [],
            'daily_pnl': [],
            'cumulative_pnl': [],
            'bankroll': [starting_bankroll]
        }
        
        current_bankroll = starting_bankroll
        total_pnl = 0
        
        for date, day_bets in daily_bets:
            # Get all possible parlays of specified size
            if len(day_bets) >= parlay_size:
                # Create all combinations of parlay_size
                parlay_combinations = list(itertools.combinations(day_bets.index, parlay_size))
                
                daily_bet_count = 0
                daily_wins = 0
                daily_pnl = 0
                
                for combo in parlay_combinations:
                    parlay_bets = day_bets.loc[list(combo)]
                    
                    # Check if all legs hit
                    all_hit = all(parlay_bets['hit'])
                    
                    if all_hit:
                        # Calculate parlay payout
                        total_odds = 1
                        for _, bet in parlay_bets.iterrows():
                            if bet['odds'] > 0:
                                total_odds *= (1 + bet['odds']/100)
                            else:
                                total_odds *= (1 + 100/abs(bet['odds']))
                        
                        payout = bet_size * total_odds
                        profit = payout - bet_size
                        daily_wins += 1
                    else:
                        profit = -bet_size
                    
                    daily_pnl += profit
                    daily_bet_count += 1
                
                # Update results
                total_pnl += daily_pnl
                current_bankroll += daily_pnl
                
                results['dates'].append(date)
                results['bets_placed'].append(daily_bet_count)
                results['bets_won'].append(daily_wins)
                results['daily_pnl'].append(daily_pnl)
                results['cumulative_pnl'].append(total_pnl)
                results['bankroll'].append(current_bankroll)
        
        # Calculate summary statistics
        total_bets = sum(results['bets_placed'])
        total_wins = sum(results['bets_won'])
        
        summary = {
            'strategy': f'EV>{ev_threshold}%, {parlay_size}-leg parlays',
            'total_bets': total_bets,
            'total_wins': total_wins,
            'win_rate': total_wins / total_bets * 100 if total_bets > 0 else 0,
            'total_pnl': total_pnl,
            'roi': total_pnl / (total_bets * bet_size) * 100 if total_bets > 0 else 0,
            'ending_bankroll': current_bankroll,
            'max_drawdown': self.calculate_max_drawdown(results['bankroll'])
        }
        
        return {'summary': summary, 'details': results}
    
    def calculate_max_drawdown(self, bankroll_history: List[float]) -> float:
        """Calculate maximum drawdown percentage"""
        peak = bankroll_history[0]
        max_dd = 0
        
        for value in bankroll_history:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            max_dd = max(max_dd, dd)
        
        return max_dd
    
    def run_all_strategies(self, ev_thresholds: List[float], parlay_sizes: List[int]):
        """
        Test all combinations of EV thresholds and parlay sizes
        """
        # First calculate EVs for all picks
        merged = self.merge_picks_with_odds()
        ev_df = self.calculate_all_evs(merged)
        
        all_results = []
        
        for ev_threshold in ev_thresholds:
            for parlay_size in parlay_sizes:
                print(f"Testing EV>{ev_threshold}% with {parlay_size}-leg parlays...")
                
                result = self.simulate_betting_strategy(
                    ev_df=ev_df,
                    ev_threshold=ev_threshold,
                    parlay_size=parlay_size
                )
                
                all_results.append(result['summary'])
        
        # Create summary DataFrame
        summary_df = pd.DataFrame(all_results)
        return summary_df, ev_df

class CorrelationAnalyzer:
    """
    Analyze correlations between different bet types
    """
    
    def __init__(self, picks_with_results: pd.DataFrame):
        self.data = picks_with_results
        
    def find_correlated_markets(self, min_occurrences: int = 20):
        """
        Find markets that tend to hit together
        """
        # Group by date to find bets that were available on the same day
        daily_groups = self.data.groupby('date')
        
        correlation_results = defaultdict(lambda: {'both_hit': 0, 'total': 0})
        
        for date, group in daily_groups:
            # Get all market pairs for this day
            markets = group['market_standard'].unique()
            
            for market1, market2 in itertools.combinations(markets, 2):
                m1_bets = group[group['market_standard'] == market1]
                m2_bets = group[group['market_standard'] == market2]
                
                # Check if both markets hit
                m1_hit_rate = m1_bets['hit'].mean()
                m2_hit_rate = m2_bets['hit'].mean()
                
                if m1_hit_rate > 0 and m2_hit_rate > 0:
                    correlation_results[(market1, market2)]['both_hit'] += 1
                
                correlation_results[(market1, market2)]['total'] += 1
        
        # Calculate correlation scores
        correlations = []
        for (m1, m2), counts in correlation_results.items():
            if counts['total'] >= min_occurrences:
                correlation_rate = counts['both_hit'] / counts['total']
                correlations.append({
                    'market1': m1,
                    'market2': m2,
                    'correlation_rate': correlation_rate,
                    'occurrences': counts['total']
                })
        
        return pd.DataFrame(correlations).sort_values('correlation_rate', ascending=False)

# Main execution function
def run_historical_ev_backtest(picks_file: str, api_key: str = None):
    """
    Main function to run the complete historical EV backtest
    """
    print("="*60)
    print("HISTORICAL EV BACKTESTING SYSTEM")
    print("="*60)
    
    # Load historical picks
    print("\n1. Loading historical picks...")
    picks_df = pd.read_csv(picks_file)
    picks_df['date'] = pd.to_datetime(picks_df['date'])
    print(f"   Loaded {len(picks_df)} historical picks")
    print(f"   Date range: {picks_df['date'].min()} to {picks_df['date'].max()}")
    
    # Initialize odds collector
    if api_key:
        print("\n2. Fetching historical odds data...")
        collector = HistoricalOddsCollector(api_key)
        
        # TODO: Fetch odds for each unique date in picks
        # This would be done in batches to respect API limits
        
        # For now, create a mock odds DataFrame for testing
        print("   [Using mock data for demonstration]")
    
    # Create mock odds data for testing (remove when API is available)
    mock_odds = create_mock_odds_data(picks_df)
    
    # Run backtests
    print("\n3. Running backtests...")
    engine = BacktestEngine(picks_df, mock_odds)
    
    # Test different strategies
    ev_thresholds = [3.0, 5.0, 7.0, 10.0]
    parlay_sizes = [2, 3, 4, 5, 6]
    
    summary_df, ev_df = engine.run_all_strategies(ev_thresholds, parlay_sizes)
    
    # Display results
    print("\n4. BACKTEST RESULTS")
    print("="*60)
    print(summary_df.to_string(index=False))
    
    # Find best strategy
    best_roi = summary_df.loc[summary_df['roi'].idxmax()]
    print(f"\n🏆 BEST STRATEGY BY ROI:")
    print(f"   {best_roi['strategy']}")
    print(f"   ROI: {best_roi['roi']:.2f}%")
    print(f"   Win Rate: {best_roi['win_rate']:.2f}%")
    
    # Run correlation analysis
    print("\n5. Running correlation analysis...")
    analyzer = CorrelationAnalyzer(picks_df)
    correlations = analyzer.find_correlated_markets()
    
    print("\n📊 TOP CORRELATED MARKETS:")
    print(correlations.head(10).to_string(index=False))
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_df.to_csv(f'backtest_results_{timestamp}.csv', index=False)
    correlations.to_csv(f'correlation_results_{timestamp}.csv', index=False)
    
    print(f"\n✅ Results saved to:")
    print(f"   - backtest_results_{timestamp}.csv")
    print(f"   - correlation_results_{timestamp}.csv")

def create_mock_odds_data(picks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Create mock odds data for testing without API
    """
    mock_odds = []
    
    for _, pick in picks_df.iterrows():
        # Create odds for multiple books
        for book in ['pinnacle', 'bet365', 'draftkings', 'fanduel']:
            # Generate realistic odds based on whether the pick hit
            if pick['hit']:
                # If it hit, make odds slightly favorable
                base_odds = np.random.choice([-120, -115, -110, -105, 100, 105])
            else:
                # If it lost, make odds slightly unfavorable  
                base_odds = np.random.choice([-130, -125, -120, -115, -110])
            
            # Add some variance between books
            odds_variance = np.random.randint(-10, 11)
            final_odds = base_odds + odds_variance
            
            mock_odds.append({
                'date': pick['date'],
                'player': pick['player_clean'] if 'player_clean' in pick else pick['player'],
                'market': pick['market_standard'] if 'market_standard' in pick else pick['market'],
                'line': pick['line'],
                'side': pick['side'],
                'odds': final_odds,
                'bookmaker': book
            })
    
    return pd.DataFrame(mock_odds)

if __name__ == "__main__":
    # Check for API key
    api_key = ODDS_API_KEY if ODDS_API_KEY != 'YOUR_API_KEY_HERE' else None
    
    if not api_key:
        print("⚠️  No API key found. Running with mock data.")
        print("   Set ODDS_API_KEY environment variable when you have a key.")
    
    # Run backtest on the combined historical data
    if os.path.exists('historical_splash_data_combined.csv'):
        run_historical_ev_backtest('historical_splash_data_combined.csv', api_key)
    else:
        print("❌ Please run backtest.py first to create historical_splash_data_combined.csv")