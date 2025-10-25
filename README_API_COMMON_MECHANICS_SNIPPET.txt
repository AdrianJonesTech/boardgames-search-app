## Popular Mechanics (API-based, recommended)

If forum scraping is unreliable in your environment, you can compute “common mechanics” directly from the BGG XML API data you already ingest with `fetch_top_games`.

This approach considers a mechanic popular if it appears on many games. It avoids brittle, JS-rendered forum pages and anti-bot issues.

Steps:
1. Ensure mechanics and games exist:
   - python manage.py fetch_mechanics
   - python manage.py fetch_top_games
2. Compute common mechanics from game data:
   - python manage.py compute_common_mechanics --top-k 30 --min-count 1
   - Flags:
     - --top-k: how many mechanics to flag as common (default 30)
     - --min-count: minimum number of games that must reference the mechanic (default 1)
3. After running, the app will:
   - Update Mechanic.mentions_count to the number of games using each mechanic.
   - Flag the top-K as Mechanic.is_common=True.
   - The search form automatically shows only common mechanics if any are flagged.

Notes:
- You can rerun this command anytime after refreshing game data.
- The existing `scrape_forum_mechanics` command remains available but is considered experimental due to the dynamic nature of BGG’s forum pages.
