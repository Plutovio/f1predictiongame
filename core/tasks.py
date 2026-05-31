"""
F1 Predictor — Celery Tasks

Scheduled tasks for automatic F1 data synchronization and prediction scoring.
"""
import logging
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_season_schedule(self, season=None):
    """Sync the full season schedule from FastF1."""
    try:
        from core.services.fastf1_sync import FastF1SyncService
        season = season or getattr(settings, 'F1_CURRENT_SEASON', 2026)
        service = FastF1SyncService(season)
        count = service.sync_schedule()
        logger.info(f"Schedule sync task complete: {count} races synced")
        return {'status': 'success', 'races_synced': count}
    except Exception as exc:
        logger.error(f"Schedule sync failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def sync_latest_results(self):
    """Sync results for the most recently completed races."""
    try:
        from core.services.fastf1_sync import FastF1SyncService
        service = FastF1SyncService()
        count = service.sync_latest_results()
        if count > 0:
            # Also score predictions after syncing results
            score_all_pending.delay()
        logger.info(f"Results sync task complete: {count} results synced")
        return {'status': 'success', 'results_synced': count}
    except Exception as exc:
        logger.error(f"Results sync failed: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_standings(self, season=None):
    """Sync championship standings from Jolpica API."""
    try:
        from core.services.fastf1_sync import FastF1SyncService
        season = season or getattr(settings, 'F1_CURRENT_SEASON', 2026)
        service = FastF1SyncService(season)
        service.sync_standings()
        logger.info("Standings sync task complete")
        return {'status': 'success'}
    except Exception as exc:
        logger.error(f"Standings sync failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def lock_expired_predictions():
    """Lock predictions for sessions that have started."""
    from core.models import Prediction
    unlocked = Prediction.objects.filter(is_locked=False)
    locked_count = 0
    for prediction in unlocked:
        if prediction.lock_if_needed():
            locked_count += 1
    if locked_count > 0:
        logger.info(f"Locked {locked_count} predictions")
    return {'status': 'success', 'locked': locked_count}


@shared_task
def score_all_pending():
    """Score all predictions that have results but no score."""
    from core.services.scoring import PredictionScorer
    scorer = PredictionScorer()
    scores = scorer.score_all_pending()
    logger.info(f"Scored {len(scores)} pending predictions")
    return {'status': 'success', 'scored': len(scores)}


@shared_task(bind=True, max_retries=2, default_retry_delay=300)
def sync_race_results(self, race_id):
    """Sync all session results for a specific race."""
    try:
        from core.models import Race
        from core.services.fastf1_sync import FastF1SyncService

        race = Race.objects.get(id=race_id)
        service = FastF1SyncService(race.season)
        count = service.sync_race_all_sessions(race)

        if count > 0:
            race.status = 'completed'
            race.is_completed = True
            race.save()

            # Score predictions for this race
            from core.services.scoring import PredictionScorer
            scorer = PredictionScorer()
            for session_type in ['qualifying', 'sprint', 'race']:
                scorer.score_race_predictions(race, session_type)

            # Create standings snapshot
            from core.services.standings import StandingsService
            standings = StandingsService(race.season)
            standings.create_standings_snapshot(race.round_number)

        return {'status': 'success', 'results_synced': count}
    except Exception as exc:
        logger.error(f"Race results sync failed: {exc}")
        raise self.retry(exc=exc)


@shared_task
def sync_driver_headshots():
    """Sync driver headshot URLs from FastF1."""
    from core.services.fastf1_sync import FastF1SyncService
    service = FastF1SyncService()
    service.sync_driver_headshots()
    return {'status': 'success'}


@shared_task
def full_data_sync(season=None):
    """Run a full data synchronization — schedule, results, standings."""
    from core.services.fastf1_sync import FastF1SyncService
    season = season or getattr(settings, 'F1_CURRENT_SEASON', 2026)
    service = FastF1SyncService(season)

    # Step 1: Seed teams/drivers if needed
    from core.models import Team
    if Team.objects.count() == 0:
        service.seed_teams_and_drivers()

    # Step 2: Sync schedule
    service.sync_schedule()

    # Step 3: Sync results for completed races
    service.sync_latest_results()

    # Step 4: Sync standings
    service.sync_standings()

    # Step 5: Sync headshots
    service.sync_driver_headshots()

    # Step 6: Score pending predictions
    from core.services.scoring import PredictionScorer
    scorer = PredictionScorer()
    scorer.score_all_pending()

    logger.info("Full data sync complete")
    return {'status': 'success'}
