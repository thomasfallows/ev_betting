
# 🧠 BRAINSTORMING SPACE

## RULES FOR CLAUDE
1. In this file, NO CODE is written
2. Only discuss concepts, methods and proper theory used within sports betting to help gain an edge over the competition.
3. Be critical, ask all questions to uncover areas that are unclear. Ask these questions and await answers.
4. Be thoughtful, bring up in depth solutions using math and good logic to re-work the model.
5. Be very very thorough, leave no stone unturned.
6. eate a full plan before touching any code

## CURRENT BRAINSTORM: [Topic]

### What I Want:
I want to critically examine our current EV calculation method for Splash Sports contests. Currently we calculate EV% = (True Probability - 57.74%) × 100. Im concerned its too simple or wrong.

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

### Your Task

1) Ask ALL questions until your fully understand how to solve the Users prompts
2) Break it down into steps if there is alot of areas to conqour and go through each at a time
3) As we solve each step, create a plan for cladue code to follow
