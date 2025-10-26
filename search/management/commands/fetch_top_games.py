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

        # Step 2: Batch-fetch details via XML API (20 at a time) with resilience
        def _safe_int(val):
            try:
                return int(val) if val not in (None, '') else None
            except Exception:
                return None

        def _safe_float(val):
            try:
                return float(val) if val not in (None, '') else None
            except Exception:
                return None

        created_count = 0
        for i in range(0, len(all_ids_list), 20):
            batch = all_ids_list[i:i+20]
            batch_str = ','.join(map(str, batch))
            api_url = f'https://boardgamegeek.com/xmlapi2/thing?id={batch_str}&stats=1'

            root = None
            try:
                api_resp = requests.get(api_url)
                api_resp.raise_for_status()
                root = ET.fromstring(api_resp.content)
                self.stdout.write(self.style.SUCCESS(f'Fetched details for batch starting at index {i} ({len(batch)} ids)'))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to fetch/parse details for batch {batch_str}: {e}. Skipping this batch.'))
                # Continue to next batch without raising
                time.sleep(1)
                continue

            for item in root.findall('item'):
                try:
                    bgg_id = _safe_int(item.get('id'))
                    if not bgg_id:
                        continue

                    name_elem = item.find('name')
                    name = name_elem.get('value', '') if name_elem is not None else ''
                    if not name:
                        continue

                    # Basic fields (safe parsing)
                    year_elem = item.find('yearpublished')
                    year = _safe_int(year_elem.get('value')) if year_elem is not None else None

                    min_p_elem = item.find('.//minplayers')
                    min_players = _safe_int(min_p_elem.get('value')) if min_p_elem is not None else None

                    max_p_elem = item.find('.//maxplayers')
                    max_players = _safe_int(max_p_elem.get('value')) if max_p_elem is not None else None

                    pt_elem = item.find('.//playingtime')
                    playing_time = _safe_int(pt_elem.get('value')) if pt_elem is not None else None

                    weight_elem = item.find('.//averageweight')
                    weight = _safe_float(weight_elem.get('value')) if weight_elem is not None else None

                    rating_elem = item.find('.//average')  # User avg rating
                    rating = _safe_float(rating_elem.get('value')) if rating_elem is not None else None

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
                        try:
                            mech_id = _safe_int(link.get('id'))
                            if not mech_id:
                                continue
                            mech_name = link.get('value', '')
                            mechanic, _ = Mechanic.objects.get_or_create(
                                bgg_id=mech_id,
                                defaults={'name': mech_name or f'Mechanic {mech_id}'}
                            )
                            game.mechanics.add(mechanic)
                        except Exception as e:
                            self.stderr.write(self.style.WARNING(f'Failed to link mechanic for game {bgg_id}: {e}'))
                            continue
                except Exception as e:
                    # Skip problematic item but keep batch processing
                    self.stderr.write(self.style.WARNING(f'Skipped an item in batch {batch_str} due to error: {e}'))
                    continue
            # Rate limit: 1s between batches (even on success)
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS(f'Ingest complete! Created/updated {created_count} games.'))