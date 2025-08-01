# API Efficiency Analysis Report

## Current Usage (Per Run)
- **Total API Calls**: ~21 (2 for game lists + 15 MLB + 4 WNBA games)
- **Total Token Cost**: ~3,480 tokens
- **Cost Breakdown**:
  - MLB: 180 tokens per game (9 markets × 2 regions × 10)
  - WNBA: 120 tokens per game (6 markets × 2 regions × 10)

## Key Findings

### 1. Region Analysis
- **Current**: Using both `us` and `us2` regions
- **Discovery**: These regions have NO overlapping sportsbooks
  - `us` provides: DraftKings, FanDuel, BetRivers, Fanatics
  - `us2` provides: ESPN BET, Bally Bet, Fliff, Hard Rock Bet
- **Recommendation**: KEEP BOTH REGIONS - they provide unique books

### 2. Market Usage Analysis
**MLB Markets Active Today**:
- singles: 30.1% of props
- total_bases: 20.1%
- runs: 18.5%
- hits: 10.8%
- strikeouts: 7.6%
- Others: <5% each

**WNBA Markets Active**:
- All 6 configured markets are being used

### 3. Sportsbook Coverage
From latest run:
- FanDuel: 336 props (29.1%)
- DraftKings: 416 props (36.0%)
- Fanatics: 268 props (23.2%)
- ESPN BET: 66 props (5.7%)
- Others: <5% each

## Optimization Recommendations

### ❌ DO NOT IMPLEMENT - Region Reduction
- Removing either region would lose 50% of sportsbooks
- This would significantly reduce EV opportunity detection
- Keep using `us,us2` for complete coverage

### ✅ SAFE OPTIMIZATION 1: Dynamic Market Selection
**Concept**: Only request markets that Splash actually has for that day
**Implementation**:
1. Query Splash props first (already doing)
2. Extract unique markets per sport
3. Only request those specific markets from The Odds API

**Potential Savings**: 
- If only 5 MLB markets active: 180 → 100 tokens per game (44% reduction)
- Typical savings: 30-50% on MLB calls

### ✅ SAFE OPTIMIZATION 2: Smart Game Filtering
**Concept**: Only fetch odds for games with Splash props
**Implementation**:
1. Extract unique games from Splash props
2. Only call API for those specific games

**Potential Savings**:
- Skip games with no Splash props
- Estimated 10-20% reduction in API calls

### ⚠️ RISKY - Book Filtering
- Could filter to only major books (DK, FD, etc.)
- BUT: Would miss arbitrage opportunities from smaller books
- NOT RECOMMENDED for EV calculations

## Estimated Total Savings
With safe optimizations:
- Current: ~3,480 tokens per run
- Optimized: ~2,000-2,500 tokens per run
- **Savings: 28-43%** while maintaining 100% data completeness

## Implementation Priority
1. **High Priority**: Dynamic market selection (biggest impact, easiest to implement)
2. **Medium Priority**: Smart game filtering (moderate impact, slightly complex)
3. **Do Not Implement**: Region or book filtering (would lose data)