"""
Script to verify all QB props from Splash are captured in our system
Compares:
1. Splash Sports API (source of truth)
2. Our splash_props database table
3. What shows on the frontend
"""

import requests
import pymysql
import sys
sys.path.append('Backend')
from config import DB_CONFIG_DICT

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def fetch_splash_qbs(sport):
    """Fetch all QB passing yards props from Splash API"""
    print(f"\n{'='*80}")
    print(f"FETCHING {sport.upper()} QB PROPS FROM SPLASH SPORTS API")
    print(f"{'='*80}")

    url = "https://api.splashsports.com/props-service/api/props"
    params = {
        "league": sport,
        "limit": 100,
        "offset": 0
    }

    all_qb_props = []

    while True:
        try:
            response = requests.get(url, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            props = data.get("data", [])
            if not props:
                break

            # Filter for passing_yards market only
            for prop in props:
                market = prop.get("type")
                if market == "passing_yards":
                    player_name = prop.get("entity_name")
                    line = prop.get("line")
                    team_info = prop.get("team", {})
                    team_abbr = team_info.get("alias") if isinstance(team_info, dict) else None

                    all_qb_props.append({
                        'player_name': player_name,
                        'line': line,
                        'team': team_abbr,
                        'market': market
                    })

            # Check if more pages
            total = data.get("total", 0)
            params["offset"] += params["limit"]
            if params["offset"] >= total:
                break

        except Exception as e:
            print(f"Error fetching from Splash: {e}")
            break

    print(f"Found {len(all_qb_props)} QB passing yards props on Splash")
    return all_qb_props


def fetch_db_qbs(sport):
    """Fetch all QB passing yards props from our database"""
    print(f"\n{'='*80}")
    print(f"CHECKING {sport.upper()} QB PROPS IN DATABASE (splash_props)")
    print(f"{'='*80}")

    conn = pymysql.connect(**DB_CONFIG_DICT)
    cursor = conn.cursor()

    query = """
    SELECT player_name, line, team_abbr, market
    FROM splash_props
    WHERE sport = %s
    AND market = 'passing_yards'
    ORDER BY player_name
    """

    cursor.execute(query, (sport,))
    results = cursor.fetchall()
    conn.close()

    db_qb_props = [{
        'player_name': row['player_name'],
        'line': float(row['line']),
        'team': row['team_abbr'],
        'market': row['market']
    } for row in results]

    print(f"Found {len(db_qb_props)} QB passing yards props in database")
    return db_qb_props


def fetch_frontend_qbs(sport):
    """Fetch what QBs are showing on the frontend via API"""
    print(f"\n{'='*80}")
    print(f"CHECKING {sport.upper()} QB PROPS ON FRONTEND")
    print(f"{'='*80}")

    # This would normally call the Flask API endpoint
    # For now, let's check what props would be used to generate stacks

    conn = pymysql.connect(**DB_CONFIG_DICT)
    cursor = conn.cursor()

    # Replicate the query from the API endpoint
    query = """
    SELECT DISTINCT
        sp.player_name,
        sp.line,
        sp.team_abbr as team,
        CASE sp.market
            WHEN 'passing_yards' THEN 'player_pass_yds'
            WHEN 'completions' THEN 'player_pass_completions'
            ELSE sp.market
        END as market,
        COALESCE(pp.home, game_context.home) as home,
        COALESCE(pp.away, game_context.away) as away,
        COUNT(DISTINCT pp.book) as book_count
    FROM splash_props sp
    LEFT JOIN (
        SELECT DISTINCT
            DATE(gamedate) as game_day,
            home,
            away,
            sport
        FROM player_props
        WHERE sport = %s
    ) game_context ON (
        DATE(sp.game_date) = game_context.game_day
        AND (game_context.home = sp.team_abbr OR game_context.away = sp.team_abbr)
        AND game_context.sport = %s
    )
    LEFT JOIN player_props pp ON (
        sp.normalized_name = pp.normalized_name
        AND ABS(sp.line - pp.line) <= 1.6
        AND pp.market = CASE sp.market
            WHEN 'passing_yards' THEN 'player_pass_yds'
            WHEN 'completions' THEN 'player_pass_completions'
            ELSE sp.market
        END
        AND pp.sport = %s
    )
    WHERE sp.sport = %s
    AND sp.market = 'passing_yards'
    GROUP BY sp.player_name, sp.line, sp.team_abbr, market, home, away
    HAVING home IS NOT NULL AND away IS NOT NULL
    ORDER BY sp.player_name
    """

    cursor.execute(query, (sport, sport, sport, sport))
    results = cursor.fetchall()
    conn.close()

    frontend_qb_props = [{
        'player_name': row['player_name'],
        'line': float(row['line']),
        'team': row['team'],
        'market': 'passing_yards',
        'book_count': row['book_count']
    } for row in results]

    print(f"Found {len(frontend_qb_props)} QB passing yards props that would show on frontend")
    return frontend_qb_props


def compare_props(splash_props, db_props, frontend_props, sport):
    """Compare the three sources and report discrepancies"""
    print(f"\n{'='*80}")
    print(f"{sport.upper()} COMPARISON RESULTS")
    print(f"{'='*80}")

    # Create sets for comparison (using player_name + line as key)
    splash_set = set((p['player_name'], p['line']) for p in splash_props)
    db_set = set((p['player_name'], p['line']) for p in db_props)
    frontend_set = set((p['player_name'], p['line']) for p in frontend_props)

    # Find discrepancies
    missing_from_db = splash_set - db_set
    missing_from_frontend = db_set - frontend_set
    extra_in_db = db_set - splash_set

    print(f"\nSUMMARY:")
    print(f"   Splash Sports:  {len(splash_props)} QBs")
    print(f"   Database:       {len(db_props)} QBs")
    print(f"   Frontend:       {len(frontend_props)} QBs")

    if not missing_from_db and not missing_from_frontend:
        print(f"\n[OK] ALL GOOD! All {len(splash_props)} Splash QB props are in database and showing on frontend")
    else:
        if missing_from_db:
            print(f"\n[ERROR] MISSING FROM DATABASE ({len(missing_from_db)} QBs):")
            for name, line in sorted(missing_from_db):
                # Find the full prop details
                full_prop = next((p for p in splash_props if p['player_name'] == name and p['line'] == line), None)
                if full_prop:
                    print(f"   - {name} ({full_prop['team']}) - Pass Yds {line}")

        if missing_from_frontend:
            print(f"\n[WARNING] IN DATABASE BUT NOT ON FRONTEND ({len(missing_from_frontend)} QBs):")
            for name, line in sorted(missing_from_frontend):
                # Find the full prop details
                full_prop = next((p for p in db_props if p['player_name'] == name and p['line'] == line), None)
                if full_prop:
                    print(f"   - {name} ({full_prop['team']}) - Pass Yds {line}")
            print(f"\n   NOTE: These QBs are in database but may not show on frontend because:")
            print(f"         1. No game_context found (no other props from same game in player_props)")
            print(f"         2. Team abbreviation doesn't match any home/away in player_props")

        if extra_in_db:
            print(f"\n[WARNING] IN DATABASE BUT NOT ON SPLASH ({len(extra_in_db)} QBs):")
            print(f"   (These are old props that should have been deleted)")
            for name, line in sorted(extra_in_db):
                full_prop = next((p for p in db_props if p['player_name'] == name and p['line'] == line), None)
                if full_prop:
                    print(f"   - {name} ({full_prop['team']}) - Pass Yds {line}")

    # Show detailed list
    print(f"\nDETAILED QB LIST FROM SPLASH:")
    print(f"{'='*80}")
    for prop in sorted(splash_props, key=lambda x: x['player_name']):
        in_db = (prop['player_name'], prop['line']) in db_set
        in_frontend = (prop['player_name'], prop['line']) in frontend_set

        status_db = "[Y]" if in_db else "[N]"
        status_fe = "[Y]" if in_frontend else "[N]"

        # Get book count if on frontend
        book_count = ""
        if in_frontend:
            fe_prop = next((p for p in frontend_props if p['player_name'] == prop['player_name'] and p['line'] == prop['line']), None)
            if fe_prop:
                book_count = f" | Books: {fe_prop['book_count']}"

        print(f"{status_db} DB | {status_fe} FE | {prop['player_name']:30s} ({prop['team']:5s}) Pass Yds {prop['line']:.1f}{book_count}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("QB PROPS VERIFICATION TOOL")
    print("="*80)

    # Check both NFL and NCAAF
    for sport in ['nfl', 'ncaaf']:
        splash_qbs = fetch_splash_qbs(sport)
        db_qbs = fetch_db_qbs(sport)
        frontend_qbs = fetch_frontend_qbs(sport)

        compare_props(splash_qbs, db_qbs, frontend_qbs, sport)

        print("\n")

    print("\n" + "="*80)
    print("VERIFICATION COMPLETE")
    print("="*80)
