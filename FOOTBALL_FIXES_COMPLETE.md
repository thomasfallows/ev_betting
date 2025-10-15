# Football Correlation Fixes - COMPLETE

## Issues Fixed

### 1. Same-Team Correlation Filter (CRITICAL)
**Problem:** QBs were showing receivers from BOTH teams in their correlation stacks
**Example:** Carson Beck (MIA) was showing Chris Bell (LOU) as a correlated receiver

**Solution:** Added team filter in `qb_anchored_parlays.py` at line 119-120:
```python
# CRITICAL: Only correlate receivers on the SAME TEAM as the QB
if qb_team and receiver.get('team') != qb_team:
    continue
```

### 2. Show All Splash QBs (Even Without Sportsbook Odds)
**Problem:** QBs in Splash Sports but not on other sportsbooks were hidden entirely

**Solution:** Changed INNER JOIN to LEFT JOIN in both NFL and NCAAF API endpoints:
- Added `game_context` subquery to get home/away from ANY prop on the same day
- Handle null EV values gracefully in Python code
- Display "N/A" for EV when no sportsbook odds available

**Files Modified:**
- `Backend/app.py` (lines 3954-4006 for NFL, lines 4063-4114 for NCAAF)

## Changes Summary

### Backend/data_scripts/qb_anchored_parlays.py
**Lines 114-120:** Added QB team extraction and same-team filter
```python
# Get QB's team
qb_team = qb_prop.get('team')

for receiver in game_receivers:
    # CRITICAL: Only correlate receivers on the SAME TEAM as the QB
    if qb_team and receiver.get('team') != qb_team:
        continue
```

### Backend/app.py - NFL API Endpoint (lines 3954-4038)
**Changed:**
- INNER JOIN → LEFT JOIN with game_context subquery
- Handle null `avg_probability` values
- Default `ou` to 'O' if null
- Set `book_count` to 0 if null

**Query Structure:**
```sql
LEFT JOIN (
    SELECT DISTINCT DATE(gamedate) as game_day, home, away, sport
    FROM player_props
    WHERE sport = 'nfl'
) game_context ON (
    DATE(sp.game_date) = game_context.game_day
    AND (game_context.home = sp.team_abbr OR game_context.away = sp.team_abbr)
)
LEFT JOIN player_props pp ON (...)
```

### Backend/app.py - NCAAF API Endpoint (lines 4063-4146)
**Same changes as NFL** - LEFT JOIN with game_context for NCAAF sport

### Backend/app.py - NFL View (lines 2438-2558)
**Changed:** Handle null EV values in both yards and completions sections
```python
if qb['ev'] is not None:
    qb_ev_class = 'ev-positive' if qb['ev'] >= 0 else 'ev-negative'
    qb_ev_display = f"{'+'if qb['ev'] >= 0 else ''}{qb['ev']:.1f}%"
else:
    qb_ev_class = 'ev-neutral'
    qb_ev_display = 'N/A'
```

### Backend/app.py - NCAAF View (lines 2783-2840)
**Same null EV handling** as NFL

### Backend/app.py - CSS Styling (3 locations)
**Added:** `.ev-neutral` class for props without sportsbook odds
```css
.ev-neutral {
    color: #888888;
}
```

## How It Works Now

### Team Filtering
1. Each prop has `team` field from `splash_props.team_abbr`
2. QB anchor extracts its team
3. Only receivers with matching team are correlated
4. Opposing team receivers are skipped

### Showing All QBs
1. Query gets ALL props from Splash (LEFT JOIN)
2. Attempts to match with sportsbook data (player_props)
3. If match found: calculate EV normally
4. If no match: EV = null, display as "N/A"
5. Game context (home/away) inferred from ANY prop on same day with that team

### Display Behavior
- **QBs with sportsbook odds:** Green/Red EV percentage
- **QBs without sportsbook odds:** Gray "N/A" text
- **Book count:** Shows actual count (0 if no sportsbook data)
- **Only same-team receivers shown**

## Testing Steps

1. **Restart Flask server:**
   ```bash
   python Backend/app.py
   ```

2. **Navigate to parlays:**
   - NFL: http://localhost:5001/ev-opportunities?view=parlays&sport=nfl
   - NCAAF: http://localhost:5001/ev-opportunities?view=parlays&sport=ncaaf

3. **Verify:**
   - ✅ QBs only show receivers from same team
   - ✅ All Splash QBs appear (even without sportsbook odds)
   - ✅ EV shows "N/A" for props without sportsbook matches
   - ✅ Book count shows 0 for props without sportsbook data

4. **Test with data:**
   ```bash
   python Backend/data_scripts/splash_scraper.py nfl ncaaf
   python Backend/data_scripts/odds_api.py nfl ncaaf
   ```

## Example Output

**Before (BROKEN):**
```
Carson Beck (MIA)
├─ Chris Bell (LOU) - WR1  ← WRONG TEAM!
└─ Caullin Lacy (MIA) - WR2
```

**After (FIXED):**
```
Carson Beck (MIA)
├─ Caullin Lacy (MIA) - WR2  ✓ Same team
└─ Malachi Toney (MIA) - WR1  ✓ Same team
```

**Splash-Only QB (No Sportsbook Odds):**
```
John Doe (OSU)
PASS YDS O 250.5 | Books: 0
N/A  ← Gray text, indicates no sportsbook coverage
```

## Status: READY TO TEST

All fixes implemented and ready for verification with real data.
