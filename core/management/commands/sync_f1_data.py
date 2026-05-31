"""
Management command to sync F1 data from FastF1 and Jolpica API.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Sync F1 data (schedule, results, standings) from FastF1 and Jolpica API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season', type=int, default=2026,
            help='Season year (default: 2026)'
        )
        parser.add_argument(
            '--schedule', action='store_true',
            help='Sync schedule only'
        )
        parser.add_argument(
            '--results', action='store_true',
            help='Sync results only'
        )
        parser.add_argument(
            '--standings', action='store_true',
            help='Sync standings only'
        )
        parser.add_argument(
            '--race', type=int, default=None,
            help='Sync specific race round number'
        )
        parser.add_argument(
            '--full', action='store_true',
            help='Run full data sync (schedule + results + standings + scoring)'
        )

    def handle(self, *args, **options):
        from core.services.fastf1_sync import FastF1SyncService
        from core.services.scoring import PredictionScorer
        from core.models import Race

        season = options['season']
        service = FastF1SyncService(season)
        scorer = PredictionScorer()

        self.stdout.write(self.style.NOTICE(f'\nF1 Data Sync -- {season} Season\n'))

        sync_all = options['full'] or not any([
            options['schedule'], options['results'], options['standings'], options['race']
        ])

        if options['schedule'] or sync_all:
            self.stdout.write('Syncing schedule...')
            try:
                count = service.sync_schedule()
                self.stdout.write(self.style.SUCCESS(f'  [OK] {count} races'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [FAIL] Failed: {e}'))

        if options['race']:
            round_num = options['race']
            self.stdout.write(f'Syncing results for Round {round_num}...')
            try:
                race = Race.objects.get(season=season, round_number=round_num)
                count = service.sync_race_all_sessions(race)
                self.stdout.write(self.style.SUCCESS(f'  [OK] {count} results'))

                # Score predictions
                for st in ['qualifying', 'sprint', 'race']:
                    scorer.score_race_predictions(race, st)
                self.stdout.write(self.style.SUCCESS('  [OK] Predictions scored'))

                # Create standings snapshot
                from core.services.standings import StandingsService
                standings_svc = StandingsService(season)
                standings_svc.create_standings_snapshot(round_num)
                self.stdout.write(self.style.SUCCESS('  [OK] Standings snapshot created'))
            except Race.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  [FAIL] Race R{round_num} not found'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [FAIL] Failed: {e}'))

        elif options['results'] or sync_all:
            self.stdout.write('Syncing latest results...')
            try:
                count = service.sync_latest_results()
                self.stdout.write(self.style.SUCCESS(f'  [OK] {count} results'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [FAIL] Failed: {e}'))

        if options['standings'] or sync_all:
            self.stdout.write('Syncing standings...')
            try:
                service.sync_standings()
                self.stdout.write(self.style.SUCCESS('  [OK] Standings synced'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  [FAIL] Failed: {e}'))

        if sync_all:
            self.stdout.write('Scoring pending predictions...')
            scores = scorer.score_all_pending()
            self.stdout.write(self.style.SUCCESS(f'  [OK] {len(scores)} predictions scored'))

        self.stdout.write(self.style.SUCCESS('\nSync complete!\n'))
