"""
F1 Predictor — Prediction Scoring Engine

Scores user predictions against actual race/qualifying/sprint results.

Scoring Rules:
  - Exact P1 prediction:     5 points
  - Exact P2 prediction:     4 points
  - Exact P3 prediction:     3 points
  - Correct driver, wrong position: 1 point each
  - Exact podium bonus (all 3 exact): 3 bonus points
  - Maximum per session:     15 points
"""
import logging
from django.db import transaction

from core.models import Prediction, PredictionScore, SessionResult

logger = logging.getLogger(__name__)

# Points for exact position match
EXACT_POSITION_POINTS = {
    1: 5,  # Exact P1
    2: 4,  # Exact P2
    3: 3,  # Exact P3
}

CORRECT_DRIVER_WRONG_POS = 1  # Driver in top 3 but wrong slot
EXACT_PODIUM_BONUS = 3  # All 3 exactly correct


class PredictionScorer:
    """Scores predictions against actual results."""

    def score_prediction(self, prediction):
        """
        Score a single prediction against actual results.

        Returns PredictionScore object or None if results aren't available.
        """
        # Get actual top 3 for this race/session
        actual_results = SessionResult.objects.filter(
            race=prediction.race,
            session_type=prediction.session_type,
            position__lte=3,
        ).order_by('position').select_related('driver')

        if actual_results.count() < 3:
            logger.info(
                f"Skipping scoring for {prediction}: "
                f"only {actual_results.count()} results available"
            )
            return None

        # Build actual podium
        actual_podium = {}
        actual_drivers = set()
        actual_p1 = actual_p2 = actual_p3 = None

        for result in actual_results:
            actual_podium[result.position] = result.driver
            actual_drivers.add(result.driver_id)
            if result.position == 1:
                actual_p1 = result.driver
            elif result.position == 2:
                actual_p2 = result.driver
            elif result.position == 3:
                actual_p3 = result.driver

        # Build predicted podium
        predicted = {
            1: prediction.p1_driver,
            2: prediction.p2_driver,
            3: prediction.p3_driver,
        }
        predicted_drivers = {
            prediction.p1_driver_id,
            prediction.p2_driver_id,
            prediction.p3_driver_id,
        }

        # Calculate score
        actual_p1 = actual_podium.get(1)
        actual_p2 = actual_podium.get(2)
        actual_p3 = actual_podium.get(3)

        exact_p1 = predicted[1].id == actual_p1.id if actual_p1 else False
        exact_p2 = predicted[2].id == actual_p2.id if actual_p2 else False
        exact_p3 = predicted[3].id == actual_p3.id if actual_p3 else False

        # Count correct drivers in wrong position
        correct_wrong_pos = 0
        for pos in [1, 2, 3]:
            pred_driver_id = predicted[pos].id
            actual_driver = actual_podium.get(pos)
            if actual_driver and pred_driver_id != actual_driver.id:
                # Driver is in the wrong position but is in actual top 3
                if pred_driver_id in actual_drivers:
                    correct_wrong_pos += 1

        # Check exact podium bonus
        exact_podium = exact_p1 and exact_p2 and exact_p3

        # Calculate total
        total = 0
        if exact_p1:
            total += EXACT_POSITION_POINTS[1]
        if exact_p2:
            total += EXACT_POSITION_POINTS[2]
        if exact_p3:
            total += EXACT_POSITION_POINTS[3]
        total += correct_wrong_pos * CORRECT_DRIVER_WRONG_POS
        if exact_podium:
            total += EXACT_PODIUM_BONUS

        # Create/update score
        with transaction.atomic():
            score, created = PredictionScore.objects.update_or_create(
                prediction=prediction,
                defaults={
                    'user': prediction.user,
                    'race': prediction.race,
                    'session_type': prediction.session_type,
                    'exact_p1': exact_p1,
                    'exact_p2': exact_p2,
                    'exact_p3': exact_p3,
                    'correct_drivers': correct_wrong_pos,
                    'exact_podium_bonus': exact_podium,
                    'total_points': total,
                    'actual_p1': actual_p1,
                    'actual_p2': actual_p2,
                    'actual_p3': actual_p3,
                }
            )

        action = "Created" if created else "Updated"
        logger.info(
            f"  {action} score for {prediction.user.username} — "
            f"{prediction.race.name} {prediction.session_type}: {total}pts"
        )
        return score

    def score_race_predictions(self, race, session_type=None):
        """Score all predictions for a given race and optional session type."""
        # First, ensure any predictions that should be locked are locked
        unlocked = Prediction.objects.filter(race=race, is_locked=False)
        for prediction in unlocked:
            prediction.lock_if_needed()

        filters = {'race': race, 'is_locked': True}
        if session_type:
            filters['session_type'] = session_type

        predictions = Prediction.objects.filter(**filters).select_related(
            'user', 'race', 'p1_driver', 'p2_driver', 'p3_driver'
        )

        scores = []
        for prediction in predictions:
            score = self.score_prediction(prediction)
            if score:
                scores.append(score)

        logger.info(f"Scored {len(scores)} predictions for {race.name}")
        return scores

    def score_all_pending(self):
        """Score all predictions that have locked or should be locked but no score yet."""
        # First, ensure any predictions that should be locked are locked
        unlocked = Prediction.objects.filter(is_locked=False)
        for prediction in unlocked:
            prediction.lock_if_needed()

        unscored = Prediction.objects.filter(
            is_locked=True,
        ).exclude(
            score__isnull=False
        ).select_related('user', 'race', 'p1_driver', 'p2_driver', 'p3_driver')

        scores = []
        for prediction in unscored:
            score = self.score_prediction(prediction)
            if score:
                scores.append(score)

        if scores:
            logger.info(f"Scored {len(scores)} pending predictions")
        return scores


def get_leaderboard(season=2026):
    """Get prediction leaderboard for a season."""
    from django.db.models import Sum, Count, Avg, Q

    leaderboard = PredictionScore.objects.filter(
        race__season=season
    ).values(
        'user__id', 'user__username'
    ).annotate(
        total_pts=Sum('total_points'),
        predictions_count=Count('id'),
        exact_podiums=Count('id', filter=Q(exact_podium_bonus=True)),
        avg_points=Avg('total_points'),
    ).order_by('-total_pts')

    return leaderboard


def get_head_to_head(user1, user2, season=2026):
    """Get head-to-head comparison between two users."""
    from django.db.models import Sum, Count, Q, Avg
    from core.models import Race

    completed_races = Race.objects.filter(
        season=season, is_completed=True
    ).order_by('round_number')

    comparison = {
        'user1': {'username': user1.username, 'wins': 0, 'total': 0, 'races': []},
        'user2': {'username': user2.username, 'wins': 0, 'total': 0, 'races': []},
        'ties': 0,
    }

    for race in completed_races:
        u1_score = PredictionScore.objects.filter(
            user=user1, race=race
        ).aggregate(total=Sum('total_points'))['total'] or 0

        u2_score = PredictionScore.objects.filter(
            user=user2, race=race
        ).aggregate(total=Sum('total_points'))['total'] or 0

        comparison['user1']['races'].append({'race': race.name, 'round': race.round_number, 'points': u1_score})
        comparison['user2']['races'].append({'race': race.name, 'round': race.round_number, 'points': u2_score})

        comparison['user1']['total'] += u1_score
        comparison['user2']['total'] += u2_score

        if u1_score > u2_score:
            comparison['user1']['wins'] += 1
        elif u2_score > u1_score:
            comparison['user2']['wins'] += 1
        else:
            comparison['ties'] += 1

    return comparison
