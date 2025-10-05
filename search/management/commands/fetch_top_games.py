from django.core.management.base import BaseCommand
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re
import time
from search.models import Game, Mechanic

class Command(BaseCommand):
    help = 'Fetch top 1000 ranked board games from BGG, ingest details and mechanics into DB'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting top 1000 games ingest...'))

        # Step 1: Scrape top 1000 IDs from ranked pages (100/page, 10 pages)
        all_ids = set()  # Use set to dedupe any issues
        base_url = 'https://boardgamegeek.com/browse/boardgame'
        params = {'sort': 'rank'}  # Explicit, though default
        for page in range(1, 11):  # Pages 1-10
            if page == 1:
                url = base_url
            else:
                url = f'{base_url}/page/{page}'
            self.stdout.write(self.style.WARNING(f'Scraping page {page}...'))
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')

            # Find the rankings table (first <table> is usually it)
            table = soup.find('table')
            if not table:
                self.stderr.write(self.style.ERROR(f'No table found on page {page}'))
                continue
            rows = table.find_all('tr')[1:]  # Skip header row

            page_ids = []
            skipped = 0
            for row in rows:
                tds = row.find_all('td')
                if len(tds) < 3:
                    skipped += 1
                    continue

                # Safe rank parsing: Skip non-game rows (e.g., footers with text like 'Expand Your Collection')
                rank_cell = tds[0]
                try:
                    rank = int(rank_cell.text.strip())
                except ValueError:
                    skipped += 1
                    continue

                # Game ID link: In second <td> (index 1, thumbnail column)
                name_cell = tds[1].find('a', href=True)
                if not name_cell:
                    skipped += 1
                    continue
                href = name_cell['href']
                match = re.search(r'/boardgame/(\d+)', href)
                if not match:
                    skipped += 1
                    continue
                bgg_id = int(match.group(1))
                page_ids.append(bgg_id)
                all_ids.add(bgg_id)  # Dedupe
                self.stdout.write(self.style.SUCCESS(f'Page {page}: Rank {rank} -> ID {bgg_id}'))

            self.stdout.write(self.style.SUCCESS(f'Page {page}: Found {len(page_ids)} new IDs (skipped {skipped})'))

            time.sleep(0.5)  # Light rate limit between pages

        all_ids_list = list(all_ids)
        self.stdout.write(self.style.SUCCESS(f'Total unique IDs: {len(all_ids_list)}. Now fetching details...'))

        # Step 2: Batch-fetch details via XML API (20 at a time) - unchanged except for minor safety
        created_count = 0
        for i in range(0, len(all_ids_list), 20):
            batch = all_ids_list[i:i+20]
            batch_str = ','.join(map(str, batch))
            api_url = f'https://boardgamegeek.com/xmlapi2/thing?id={batch_str}&stats=1'
            api_resp = requests.get(api_url)
            api_resp.raise_for_status()
            root = ET.fromstring(api_resp.content)

            for item in root.findall('item'):
                bgg_id = int(item.get('id'))
                name_elem = item.find('name')
                name = name_elem.get('value', '') if name_elem is not None else ''

                if not name:  # Skip invalid
                    continue

                # Basic fields
                year_elem = item.find('yearpublished')
                year = int(year_elem.get('value')) if year_elem is not None and year_elem.get('value') else None

                min_p_elem = item.find('.//minplayers')
                min_players = int(min_p_elem.get('value')) if min_p_elem is not None else None

                max_p_elem = item.find('.//maxplayers')
                max_players = int(max_p_elem.get('value')) if max_p_elem is not None else None

                pt_elem = item.find('.//playingtime')
                playing_time = int(pt_elem.get('value')) if pt_elem is not None and pt_elem.get('value') else None

                weight_elem = item.find('.//averageweight')
                weight = float(weight_elem.get('value', 0)) if weight_elem is not None else None

                rating_elem = item.find('.//average')  # User avg rating
                rating = float(rating_elem.get('value', 0)) if rating_elem is not None else None

                thumbnail = item.find('thumbnail').text if item.find('thumbnail') is not None else None

                desc_elem = item.find('description')
                description = desc_elem.text if desc_elem is not None else None

                # Create/update game
                game, created = Game.objects.get_or_create(
                    bgg_id=bgg_id,
                    defaults={
                        'name': name,
                        'year': year,
                        'min_players': min_players,
                        'max_players': max_players,
                        'playing_time': playing_time,
                        'weight': weight,
                        'rating': rating,
                        'thumbnail': thumbnail,
                        'description': description,
                    }
                )
                if created:
                    created_count += 1

                # Link mechanics
                for link in item.findall("link[@type='boardgamemechanic']"):
                    mech_id = int(link.get('id'))
                    mech_name = link.get('value', '')
                    mechanic, _ = Mechanic.objects.get_or_create(
                        bgg_id=mech_id,
                        defaults={'name': mech_name}
                    )
                    game.mechanics.add(mechanic)

            # Rate limit: 1s between batches
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS(f'Ingest complete! Created/updated {created_count} games.'))