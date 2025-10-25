from django.core.management.base import BaseCommand
from django.db.models import F
from search.models import Mechanic
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin, urlparse, urlsplit, parse_qs, urlencode, urlunsplit


class Command(BaseCommand):
    help = (
        "Scrape BGG forum/listing or thread URLs and count mentions of mechanics. "
        "Updates Mechanic.mentions_count and flags top-K as is_common."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'urls', nargs='+', help='One or more BGG forum listing or thread URLs to scrape'
        )
        parser.add_argument(
            '--max-threads', type=int, default=200,
            help='Maximum number of unique thread pages to visit in total (default: 200)'
        )
        parser.add_argument(
            '--max-depth', type=int, default=1,
            help='Depth for following pagination from listing pages (default: 1)'
        )
        parser.add_argument(
            '--top-k', type=int, default=30,
            help='Number of top mechanics to flag as common (default: 30)'
        )
        parser.add_argument(
            '--sleep', type=float, default=0.5,
            help='Seconds to sleep between HTTP requests (default: 0.5)'
        )

    def handle(self, *args, **options):
        urls = options['urls']
        max_threads = options['max_threads']
        max_depth = options['max_depth']
        top_k = options['top_k']
        delay = options['sleep']

        # HTTP session with sane defaults to avoid being blocked
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
        })
        timeout = 20
        retries = 3
        backoff = 1.5

        # Preload mechanics and compile regexes for word-boundary, case-insensitive search
        mechanics = list(Mechanic.objects.all().only('id', 'name'))
        if not mechanics:
            self.stderr.write(self.style.ERROR('No mechanics in DB. Run fetch_mechanics first.'))
            return

        mech_patterns = []
        for m in mechanics:
            # Escape regex specials and use word boundaries where possible
            name = m.name.strip()
            if not name:
                continue
            pattern = re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE)
            mech_patterns.append((m.id, pattern))

        visited_threads = set()
        aggregated_texts = []  # list of page texts from thread pages

        for start_url in urls:
            try:
                self.stdout.write(self.style.WARNING(f'Fetching start URL: {start_url}'))
                text_pages, new_threads = self._collect_from_url(session, start_url, max_depth, max_threads - len(visited_threads), delay, timeout, retries, backoff)
                for turl, page_text in text_pages:
                    if turl in visited_threads:
                        continue
                    visited_threads.add(turl)
                    aggregated_texts.append(page_text)
                if len(visited_threads) >= max_threads:
                    break
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error processing {start_url}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Collected {len(aggregated_texts)} thread pages to analyze.'))

        # Count mentions
        counts = {m.id: 0 for m in mechanics}
        for page_text in aggregated_texts:
            for mid, patt in mech_patterns:
                try:
                    matches = patt.findall(page_text)
                    if matches:
                        counts[mid] += len(matches)
                except Exception:
                    # Skip problematic regex/page combo
                    continue

        total_mentions = sum(counts.values())
        self.stdout.write(self.style.SUCCESS(f'Total mechanic mentions found: {total_mentions}'))

        # Persist: update mentions_count and flag top-K
        # First, reset is_common
        Mechanic.objects.update(is_common=False)

        # Bulk update mentions_count in small batches
        batch = []
        for mid, c in counts.items():
            batch.append((mid, c))
        # Use simple loop updates to avoid complexity; DB size is small
        updated = 0
        for mid, c in batch:
            updated += Mechanic.objects.filter(id=mid).update(mentions_count=c)
        self.stdout.write(self.style.SUCCESS(f'Updated mentions_count for {updated} mechanics.'))

        # Determine top-K by mentions_count (excluding zeros)
        top_ids = list(
            Mechanic.objects.filter(mentions_count__gt=0)
            .order_by('-mentions_count', 'name')
            .values_list('id', flat=True)[:top_k]
        )
        if top_ids:
            Mechanic.objects.filter(id__in=top_ids).update(is_common=True)
            top_names = list(Mechanic.objects.filter(id__in=top_ids).order_by('-mentions_count').values_list('name', 'mentions_count'))
            self.stdout.write(self.style.SUCCESS(f'Flagged {len(top_ids)} mechanics as common.'))
            for name, c in top_names[:10]:
                self.stdout.write(self.style.NOTICE if hasattr(self.style, 'NOTICE') else self.style.SUCCESS(f'Top: {name} ({c})'))
        else:
            self.stdout.write(self.style.WARNING('No mechanics had mentions > 0; nothing flagged as common.'))

        self.stdout.write(self.style.SUCCESS('Scraping complete.'))

    def _fetch(self, session: requests.Session, url: str, timeout: int, retries: int, backoff: float, delay: float):
        last_err = None
        for attempt in range(1, retries + 1):
            try:
                resp = session.get(url, timeout=timeout)
                status = resp.status_code
                clen = resp.headers.get('Content-Length') or len(resp.content)
                self.stdout.write(self.style.WARNING(f'GET {url} -> {status} ({clen} bytes) [attempt {attempt}]'))
                # Retry on 429 or 5xx
                if status == 429 or 500 <= status < 600:
                    last_err = Exception(f'HTTP {status}')
                elif status == 403:
                    # Likely blocked; don't hammer further
                    self.stderr.write(self.style.ERROR(f'HTTP 403 for {url}. Consider increasing --sleep or retrying later.'))
                    return None
                else:
                    resp.raise_for_status()
                    time.sleep(delay)
                    return resp
            except Exception as e:
                last_err = e
            # Backoff before next attempt if not last
            if attempt < retries:
                time.sleep(backoff * attempt)
        self.stderr.write(self.style.ERROR(f'Failed to fetch {url}: {last_err}'))
        return None

    def _collect_from_url(self, session: requests.Session, url: str, max_depth: int, remaining_threads: int, delay: float, timeout: int, retries: int, backoff: float):
        """
        Given a forum listing or thread URL, collect thread page texts up to limits.
        Returns: ([(thread_url, page_text), ...], count)
        """
        collected = []
        visited = set()
        queue = [(url, 0)]

        # If starting from the modern forums search app (JS-rendered), also enqueue legacy server-rendered search pages
        try:
            us = urlsplit(url)
            if 'boardgamegeek.com' in us.netloc and us.path.startswith('/forums/search'):
                qs = parse_qs(us.query)
                term = qs.get('searchTerm', [''])[0]
                if term:
                    legacy_thread = f"https://boardgamegeek.com/geeksearch.php?action=search&objecttype=thread&q={requests.utils.quote(term)}"
                    legacy_article = f"https://boardgamegeek.com/geeksearch.php?action=search&objecttype=article&q={requests.utils.quote(term)}"
                    queue.append((legacy_thread, 0))
                    queue.append((legacy_article, 0))
                    self.stdout.write(self.style.WARNING(f'Enqueued legacy search pages for term "{term}"'))
        except Exception:
            pass

        while queue and remaining_threads > 0:
            current, depth = queue.pop(0)
            resp = self._fetch(session, current, timeout, retries, backoff, delay)
            if resp is None:
                continue

            soup = BeautifulSoup(resp.content, 'lxml')

            # If already a thread/article/post URL, capture its text content
            if ('/thread/' in current) or ('/article/' in current) or ('/post/' in current):
                text = soup.get_text(separator=' ', strip=True)
                if text:
                    collected.append((current, text))
                    remaining_threads -= 1
                else:
                    self.stdout.write(self.style.WARNING(f'Empty content at {current}, skipping.'))
                continue

            # Otherwise treat as listing page: enqueue thread links and simple pagination
            found_links = 0
            enqueued = 0
            for a in soup.find_all('a', href=True):
                href = a['href']
                abs_url = urljoin(current, href)
                found_links += 1
                if (('/thread/' in href) or ('/article/' in href) or ('/post/' in href)) and abs_url not in visited and remaining_threads > 0:
                    visited.add(abs_url)
                    queue.append((abs_url, depth + 1))
                    enqueued += 1
                # Basic pagination heuristics: links containing '/page/' or 'page=' on same host
                elif depth < max_depth:
                    if ('/page/' in href or 'page=' in href or 'pageid=' in href) and urlparse(abs_url).netloc == urlparse(current).netloc:
                        next_url = abs_url
                        if next_url not in visited:
                            visited.add(next_url)
                            queue.append((next_url, depth + 1))

            # If no anchors discovered, try regex extraction on raw HTML (JS-rendered or obfuscated links)
            if enqueued == 0 and remaining_threads > 0:
                html = resp.text
                regex_patterns = [
                    r"https?://[^\s\"']*(?:boardgamegeek|geekdo)\.com/(?:thread|article|post)/[^\s\"']+",
                    r"/(?:thread|article|post)/[\w\-\./]+",
                ]
                matches = set()
                for rp in regex_patterns:
                    try:
                        for m in re.findall(rp, html):
                            try:
                                absu = urljoin(current, m)
                                if absu not in visited and remaining_threads > 0:
                                    if ('/thread/' in absu) or ('/article/' in absu) or ('/post/' in absu):
                                        visited.add(absu)
                                        queue.append((absu, depth + 1))
                                        enqueued += 1
                                        matches.add(absu)
                            except Exception:
                                continue
                    except re.error:
                        pass
                if matches:
                    self.stdout.write(self.style.WARNING(f'Regex extracted {len(matches)} candidate links from HTML.'))

            self.stdout.write(self.style.WARNING(f'Parsed links on {current}: scanned {found_links}, enqueued {enqueued} thread/article/post links.'))

            # Fallback: if we still couldn't find any detailed links at this level, count the listing page text itself once
            if enqueued == 0 and remaining_threads > 0:
                page_text = soup.get_text(separator=' ', strip=True)
                if page_text:
                    collected.append((current, page_text))
                    remaining_threads -= 1

        return collected, len(collected)
