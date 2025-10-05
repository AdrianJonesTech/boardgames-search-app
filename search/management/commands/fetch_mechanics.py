from django.core.management.base import BaseCommand
import requests
import xml.etree.ElementTree as ET
from search.models import Mechanic

class Command(BaseCommand):
    help = 'Fetch all mechanics from BGG API and populate the database'

    def handle(self, *args, **options):
        letters = list('abcdefghijklmnopqrstuvwxyz')
        for letter in letters:
            self.stdout.write(self.style.SUCCESS(f'Fetching mechanics starting with {letter}'))
            url = f"https://boardgamegeek.com/xmlapi2/search?query={letter}&type=boardgamemechanic"
            try:
                response = requests.get(url)
                response.raise_for_status()
                root = ET.fromstring(response.content)
                count = 0
                skipped = 0
                for item in root.findall('item'):
                    bgg_id = int(item.get('id'))
                    name_elem = item.find('name')
                    if name_elem is not None:
                        name = name_elem.attrib['value']
                        if name and name.strip():  # Skip if name is None or empty/whitespace
                            mechanic, created = Mechanic.objects.get_or_create(
                                bgg_id=bgg_id, defaults={'name': name.strip()}
                            )
                            if created:
                                count += 1
                        else:
                            skipped += 1
                            self.stdout.write(self.style.WARNING(f'Skipped mechanic ID {bgg_id}: empty name'))
                    else:
                        skipped += 1
                        self.stdout.write(self.style.WARNING(f'Skipped mechanic ID {bgg_id}: no name element'))
                self.stdout.write(self.style.SUCCESS(f'Added/updated {count} mechanics for letter {letter} (skipped {skipped})'))
                import time
                time.sleep(0.2)  # Light rate limiting
            except Exception as e:
                self.stderr.write(f'Error fetching {letter}: {e}')
        self.stdout.write(self.style.SUCCESS('Mechanics fetch complete!'))
