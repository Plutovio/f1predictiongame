"""
Management command to score predictions.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Score all pending predictions or re-score specific race predictions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--race', type=int, default=None,
            help='Score predictions for a specific race round number'
        )
        parser.add_argument(
            '--season', type=int, default=2026,
            help='Season year (default: 2026)'
        )
        parser.add_argument(
            '--rescore', action='store_true',
            help='Re-score all predictions (even already scored ones)'
        )

    def handle(self, *args, **options):
        from core.services.scoring import PredictionScorer
        from core.models import Race, Prediction

        scorer = PredictionScorer()

        if options['race']:
            try:
                race = Race.objects.get(
                    season=options['season'],
                    round_number=options['race']
                )
                self.stdout.write(f'Scoring predictions for {race.name}...')

                for session_type in ['qualifying', 'sprint', 'race']:
                    scores = scorer.score_race_predictions(race, session_type)
                    if scores:
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ {len(scores)} {session_type} predictions scored'
                        ))

            except Race.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f'Race R{options["race"]} not found for {options["season"]}'
                ))
        elif options['rescore']:
            self.stdout.write('Re-scoring ALL predictions...')
            predictions = Prediction.objects.filter(
                is_locked=True,
                race__season=options['season']
            ).select_related('user', 'race', 'p1_driver', 'p2_driver', 'p3_driver')

            count = 0
            for pred in predictions:
                score = scorer.score_prediction(pred)
                if score:
                    count += 1

            self.stdout.write(self.style.SUCCESS(f'✓ Re-scored {count} predictions'))
        else:
            self.stdout.write('Scoring pending predictions...')
            scores = scorer.score_all_pending()
            self.stdout.write(self.style.SUCCESS(f'✓ Scored {len(scores)} predictions'))
