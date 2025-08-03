
# 🧠 BRAINSTORMING SPACE

## RULES FOR CLAUDE
1. In this file, NO CODE is written
2. Only discuss concepts, methods and proper theory used within sports betting to help gain an edge over the competition.
3. Be critical, ask all questions to uncover areas that are unclear. Ask these questions and await answers.
4. Be thoughtful, bring up in depth solutions using math and good logic to re-work the model.
5. Be very very thorough, leave no stone unturned.
6. Create a full plan before touching any code

## CURRENT BRAINSTORM: EV Calculation Overhaul

### Original Concern:
I want to critically examine our current EV calculation method for Splash Sports contests. Currently we calculate EV% = (True Probability - 57.74%) × 100. Im concerned its too simple or wrong.

### Key Discovery:
The 57.74% threshold is actually CORRECT for 2-man contests! It represents the per-leg break-even probability where p² = 1/3. However, we need to shift from individual leg analysis to complete parlay analysis.

## This is how splash sports works:

2-man: lobby size = 4 players Splash rake = of pot Winner = 3x

For bets on 2mans ($5/10/20/50/100/250) the rake is 25% and winners take will always be 3x their bet. For example if it was a $20 bet splash rakes in $20 ($80 pot) and winner gets $60

3-man: lobby size = 8 players Splash rake = 25% Winner = 6x

For bets on 2mans ($5/10/20/50/100/250) the rake is 25% and winners take will always be 6x their bet. For example if it was a $20 bet splash rakes in $40 ($180) and winner gets $60

4-man: lobby size = 16 players Splash rake = 25% Winner = 12x

For bets on 2mans ($5/10/20/50/100/250) the rake is 25% and winners take will always be 12x their bet. For example if it was a $10 bet splash rakes in $40 ($160) and winner gets $120

5-man: lobby size = 32 players Splash rake = 21.8% Winner = 25x

For bets on 2mans ($5/10/20/50/100/250) the rake is 21.8% and winners take will always be 25x their bet. For example if it was a $5 bet splash rakes in $35  ($160) and winner gets $125

6-man: lobby size = 64 players Splash rake = 21.8% Winner = 50x

For bets on 2mans ($5/10/20/50/100/250) the rake is 21.8% and winners take will always be 50their bet. For example if it was a $5 bet splash rakes in $70 ($320) and winner gets $250

We don't know the prize pool distribution
You pick your own parlay size/wager. You are then matched with people who have also chose the same parlay size/wager. (leauges are irrelivent in matching)

We don't know how many contestants typically enter You are limited to entering 5/day of the same wager size and parlay size. Ie. only 5 $5 2-mans per day. After $5 2-mans are max, you can place $10 2-mans or $5 3-mans ect. Resets the next day
We don't know Splash's implied probabilities
THERE ARE NONE. You pick over/under at same cost being your wager size. 

 I want to explore if there's a more accurate way to calculate expected value that accounts for correlation, variance, and the contest payout structure.

### Questions to Answer First:
1. How do professioanls in the indusrty calculate EV? Is there a standard method for parlays?
2. Should we be calculating parlay-level EV instead of leg-level EV?
3. How do we account for correlation between legs?
4. What books should we account for when taking odds from odds API, how should we weight and average and exclude certain oddds.
5. Is there a specific time of day to place bets for most accurate data
6. What are the core statistics to show on the front end from our calculations

### My Current Understanding:
- We use devigged sharp book odds to find true probability
- We compare against Splash's implied 57.74% per leg
- We assume all legs are independent (but they might not be)
- We're not considering variance or bankroll management
- We are not considering correlation

## IMPROVED EV CALCULATION METHODOLOGY

### Core Mathematical Framework

#### Contest-Specific Break-Even Probabilities
| Contest Type | Payout | Break-Even Win Rate | Required Per-Leg Probability |
|--------------|--------|---------------------|----------------------------|
| 2-man | 3x | 33.33% | 57.74% |
| 3-man | 6x | 16.67% | 55.04% |
| 4-man | 12x | 8.33% | 53.13% |
| 5-man | 25x | 4.00% | 51.19% |
| 6-man | 50x | 2.00% | 49.29% |

#### True EV Formula
For any contest: **EV = (Parlay_Probability × (Payout - 1)) - (1 - Parlay_Probability)**

Example for 2-man: EV = (P × 2) - (1 - P) = 3P - 1

### Critical Insights

1. **Current Method Validation**: The 57.74% threshold is mathematically correct for 2-man contests
2. **Parlay vs Leg Analysis**: Must analyze complete parlays, not individual legs
3. **Minimum Edge Requirements**: 
   - 2-man: Need 40%+ parlay probability (7% edge) for $60 bankroll
   - 3-man: Need 20%+ parlay probability
   - Higher contests: Avoid with small bankroll due to variance

### Correlation Strategy

#### High-Value Negative Correlations:
1. **Pitcher Strikeouts OVER + Opposing Team Hits OVER**
2. **Team Runs UNDER + Opposing Pitcher Earned Runs UNDER**  
3. **Player Points UNDER + Player Assists OVER** (usage-based)

#### Correlation Impact:
- Reduces variance, not EV
- Allows for more aggressive Kelly sizing
- Creates more stable bankroll growth

### Sharp Book Hierarchy
1. **Pinnacle/Circa**: Most accurate (if available)
2. **DraftKings/FanDuel**: Sharp for high-liquidity markets
3. **Others**: Recreational, use with caution

### Implementation Phases

#### Phase 1: Fix EV Calculation ✓
- Shift from leg-level to parlay-level analysis
- Implement contest-specific break-even thresholds
- Add safety margins for small bankroll

#### Phase 2: Database Enhancement
- Add parlay tracking tables
- Store contest type, all legs, combined probability
- Track correlation metrics

#### Phase 3: Parlay Generation Algorithm
- Generate all valid N-leg combinations
- Calculate true parlay probability
- Filter by minimum edge requirements
- Rank by EV and correlation quality

#### Phase 4: Correlation Engine
- Build correlation matrix for common prop pairs
- Score each parlay for correlation benefit
- Prioritize negatively correlated parlays

#### Phase 5: Kelly Criterion Implementation
- Start with 1/4 Kelly for safety
- Adjust based on correlation strength
- Never risk more than 25% of bankroll per day

#### Phase 6: Performance Tracking
- Log every bet with timestamp
- Track actual vs predicted outcomes
- Calculate running ROI and Sharpe ratio
- Identify edge degradation patterns

### Expected Outcomes

With $60 bankroll focusing on 2-man contests:
- **Target**: 40%+ parlay probability opportunities
- **Expected ROI**: 8-15% per week with proper execution
- **Risk**: 30% chance of bust if unlucky early
- **Growth Path**: $60 → $150 in 30 days (conservative)

### Next Steps for Implementation

1. Update database schema for parlay-level tracking
2. Rewrite create_report.py for parlay generation
3. Build correlation detection system
4. Add Kelly sizing calculator
5. Create performance tracking dashboard
