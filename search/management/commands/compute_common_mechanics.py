from django.core.management.base import BaseCommand
from django.db.models import Count
from search.models import Mechanic, Game


class Command(BaseCommand):
    help = (
        "Compute common mechanics using existing game data from the BGG XML API.\n"
        "Counts how many Games reference each Mechanic (usage count), stores it in\n"
        "Mechanic.mentions_count, and flags the top-K as Mechanic.is_common.\n"
        "This avoids brittle forum scraping and uses authoritative API data already\n"
        "ingested by the fetch_top_games command."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--top-k', type=int, default=30,
            help='Number of top mechanics to flag as common (default: 30)'
        )
        parser.add_argument(
            '--min-count', type=int, default=1,
            help='Minimum usage count required to be eligible for common (default: 1)'
        )

    def handle(self, *args, **options):
        top_k = options['top_k']
        min_count = options['min_count']

        total_games = Game.objects.count()
        if total_games == 0:
            self.stderr.write(self.style.ERROR(
                'No games found. Run "python manage.py fetch_top_games" first.'
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f'Computing mechanic popularity from {total_games} games...'
        ))

        # Reset is_common first
        Mechanic.objects.update(is_common=False)

        # Annotate usage counts via reverse m2m relation (related_query_name defaults to model name: "game")
        qs = (
            Mechanic.objects
            .annotate(usage_count=Count('game', distinct=True))
            .order_by('-usage_count', 'name')
        )

        # Update mentions_count for all mechanics in small batches
        updated = 0
        batch = []
        for mech in qs:
            batch.append((mech.id, mech.usage_count))
        for mid, cnt in batch:
            updated += Mechanic.objects.filter(id=mid).update(mentions_count=cnt)
        self.stdout.write(self.style.SUCCESS(f'Updated mentions_count for {updated} mechanics.'))

        # Flag top-K mechanics with usage_count >= min_count
        eligible = list(
            qs.filter(usage_count__gte=min_count)
              .values_list('id', flat=True)[:top_k]
        )
        if eligible:
            Mechanic.objects.filter(id__in=eligible).update(is_common=True)
            top_names = list(
                Mechanic.objects.filter(id__in=eligible)
                .order_by('-mentions_count', 'name')
                .values_list('name', 'mentions_count')
            )
            self.stdout.write(self.style.SUCCESS(f'Flagged {len(eligible)} mechanics as common.'))
            for name, c in top_names[:10]:
                # Use NOTICE if available (Django 5 may not have it in all themes)
                self.stdout.write(getattr(self.style, 'NOTICE', self.style.SUCCESS)(f'Top: {name} ({c})'))
        else:
            self.stdout.write(self.style.WARNING('No mechanics met the min-count threshold; none flagged as common.'))

        self.stdout.write(self.style.SUCCESS('Computation complete.'))
