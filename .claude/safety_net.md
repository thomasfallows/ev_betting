# 🛡️ SAFETY NET

## Before ANY changes:
1. Run verification commands (see project.md)
2. Commit to git if tests pass
3. Tell me what specific file you're changing

## If something breaks:
1. First, check what changed: `git diff`
2. If unsure, revert: `git reset --hard`
3. Re-read the WORKING STATE in project.md

## Common Fixes:
- "No sport column" error: Check database_migration.py was run
- "Module not found" error: Check sys.path additions in files
- "EV calculation wrong": Verify SPLASH_IMPLIED_PROB = 0.5774