import urllib.parse
import re

def normalize_player_for_url(player_name):
    """Normalize player name for URL usage"""
    # Remove accents and special characters
    name = player_name.lower()
    name = re.sub(r'[áàâã]', 'a', name)
    name = re.sub(r'[éèê]', 'e', name)
    name = re.sub(r'[íì]', 'i', name)
    name = re.sub(r'[óòô]', 'o', name)
    name = re.sub(r'[úù]', 'u', name)
    name = re.sub(r'[ñ]', 'n', name)
    name = re.sub(r'[^\w\s-]', '', name)  # Remove special chars except hyphens
    name = re.sub(r'\s+', '-', name)  # Replace spaces with hyphens
    return name.strip('-')

def get_market_display_name(market_type):
    """Convert internal market names to display names"""
    market_map = {
        'batter_hits': 'hits',
        'batter_runs_scored': 'runs-scored', 
        'batter_singles': 'singles',
        'batter_total_bases': 'total-bases',
        'batter_rbis': 'rbis',
        'pitcher_strikeouts': 'strikeouts',
        'pitcher_outs': 'outs-recorded',
        'pitcher_hits_allowed': 'hits-allowed',
        'pitcher_earned_runs': 'earned-runs'
    }
    return market_map.get(market_type, market_type.replace('_', '-'))

def build_fanduel_url(player_name, market_type, line, over_under, home_team=None, away_team=None):
    """Build FanDuel direct prop URL"""
    base_url = "https://sportsbook.fanduel.com"
    
    # FanDuel URL pattern research needed - this is a best guess
    # They often use: /navigation/mlb-player-props
    player_url = normalize_player_for_url(player_name)
    market_display = get_market_display_name(market_type)
    
    # FanDuel often structures like: /mlb/player-props/[player-name]/[market]
    url = f"{base_url}/navigation/mlb-player-props?player={player_url}&market={market_display}&line={line}&side={over_under.lower()}"
    
    return url

def build_draftkings_url(player_name, market_type, line, over_under, home_team=None, away_team=None):
    """Build DraftKings direct prop URL"""
    base_url = "https://sportsbook.draftkings.com"
    
    # DraftKings URL pattern - they use different structure
    player_url = normalize_player_for_url(player_name) 
    market_display = get_market_display_name(market_type)
    
    # DraftKings often uses: /leagues/baseball/mlb/player-props
    url = f"{base_url}/leagues/baseball/mlb/player-props?search={player_url}&market={market_display}"
    
    return url

def build_betmgm_url(player_name, market_type, line, over_under, home_team=None, away_team=None):
    """Build BetMGM direct prop URL"""
    base_url = "https://sports.betmgm.com"
    
    player_url = normalize_player_for_url(player_name)
    
    # BetMGM structure: /en/sports/baseball-23/betting/usa-9/major-league-baseball-75
    url = f"{base_url}/en/sports/baseball-23/betting/usa-9/major-league-baseball-75?search={player_url}"
    
    return url

def build_caesars_url(player_name, market_type, line, over_under, home_team=None, away_team=None):
    """Build Caesars direct prop URL"""
    base_url = "https://www.caesars.com/sportsbook"
    
    player_url = normalize_player_for_url(player_name)
    
    # Caesars structure
    url = f"{base_url}/us/sports/baseball/mlb/player-props?player={player_url}"
    
    return url

def build_betrivers_url(player_name, market_type, line, over_under, home_team=None, away_team=None):
    """Build BetRivers direct prop URL"""
    base_url = "https://pa.betrivers.com"  # State-specific
    
    player_url = normalize_player_for_url(player_name)
    
    url = f"{base_url}/?page=sportsbook&sport=baseball&league=mlb&category=player-props&search={player_url}"
    
    return url

def build_fanatics_url(player_name, market_type, line, over_under, home_team=None, away_team=None):
    """Build Fanatics direct prop URL"""
    base_url = "https://sportsbook.fanatics.com"
    
    player_url = normalize_player_for_url(player_name)
    
    url = f"{base_url}/sports/baseball/mlb/player-props?search={player_url}"
    
    return url

def build_espn_url(player_name, market_type, line, over_under, home_team=None, away_team=None):
    """Build ESPN BET direct prop URL"""
    base_url = "https://sportsbook.espn.com"
    
    player_url = normalize_player_for_url(player_name)
    
    url = f"{base_url}/sports/baseball/mlb/player-props?player={player_url}"
    
    return url

def build_sportsbook_urls(player_name, market_type, line, over_under, home_team=None, away_team=None):
    """
    Build direct URLs to specific props on each sportsbook
    Returns dictionary with sportsbook names as keys and URLs as values
    """
    
    urls = {}
    
    # Build URLs for each sportsbook
    try:
        urls['FanDuel'] = build_fanduel_url(player_name, market_type, line, over_under, home_team, away_team)
    except Exception as e:
        urls['FanDuel'] = "https://sportsbook.fanduel.com/navigation/mlb"
    
    try:
        urls['DraftKings'] = build_draftkings_url(player_name, market_type, line, over_under, home_team, away_team)
    except Exception as e:
        urls['DraftKings'] = "https://sportsbook.draftkings.com/leagues/baseball/mlb"
    
    try:
        urls['BetMGM'] = build_betmgm_url(player_name, market_type, line, over_under, home_team, away_team)
    except Exception as e:
        urls['BetMGM'] = "https://sports.betmgm.com/en/sports/baseball-23"
    
    try:
        urls['Caesars'] = build_caesars_url(player_name, market_type, line, over_under, home_team, away_team)
    except Exception as e:
        urls['Caesars'] = "https://www.caesars.com/sportsbook/us/sports/baseball/mlb"
    
    try:
        urls['BetRivers'] = build_betrivers_url(player_name, market_type, line, over_under, home_team, away_team)
    except Exception as e:
        urls['BetRivers'] = "https://pa.betrivers.com/?page=sportsbook&sport=baseball"
    
    try:
        urls['Fanatics'] = build_fanatics_url(player_name, market_type, line, over_under, home_team, away_team)
    except Exception as e:
        urls['Fanatics'] = "https://sportsbook.fanatics.com/sports/baseball/mlb"
    
    try:
        urls['ESPN_BET'] = build_espn_url(player_name, market_type, line, over_under, home_team, away_team)
    except Exception as e:
        urls['ESPN_BET'] = "https://sportsbook.espn.com/sports/baseball/mlb"
    
    return urls

def format_odds_link(odds, sportsbook, player_name, market_type, line, over_under, home_team=None, away_team=None):
    """
    Format an odds value as a clickable link to the specific prop
    """
    if odds is None or odds == 0:
        return '<td class="odds-cell">-</td>'
    
    # Build the URL for this specific sportsbook
    urls = build_sportsbook_urls(player_name, market_type, line, over_under, home_team, away_team)
    url = urls.get(sportsbook, '#')
    
    # Format the odds display
    if odds > 0:
        odds_display = f"+{odds}"
        odds_class = "odds-positive"
    else:
        odds_display = str(odds)
        odds_class = "odds-negative"
    
    # Create the clickable link
    link_html = f'''
    <td class="odds-cell">
        <a href="{url}" 
           target="_blank" 
           class="{odds_class} odds-link"
           title="Click to bet {player_name} {market_type} {over_under} {line} at {sportsbook} ({odds_display})">
            {odds_display}
        </a>
    </td>
    '''
    
    return link_html

# Test the URL builder
if __name__ == "__main__":
    # Test with example data
    test_player = "Chas McCormick"
    test_market = "batter_hits" 
    test_line = 0.5
    test_ou = "U"
    
    print("Testing URL Builder:")
    print(f"Player: {test_player}")
    print(f"Market: {test_market} {test_ou} {test_line}")
    print()
    
    urls = build_sportsbook_urls(test_player, test_market, test_line, test_ou)
    
    for sportsbook, url in urls.items():
        print(f"{sportsbook}: {url}")
    
    print("\nTesting odds link formatting:")
    link = format_odds_link(-110, "FanDuel", test_player, test_market, test_line, test_ou)
    print(link)