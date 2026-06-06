"""
Management command to sync F1 results and standings using ONLY the Jolpica API.
No FastF1 dependency — works on Render free plan without heavy downloads.
"""
import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

JOLPICA_BASE = 'https://api.jolpi.ca/ergast/f1'

# Map from Jolpica driver codes to our abbreviations (for any mismatches)
DRIVER_CODE_MAP = {
    # Jolpica code -> our abbreviation
    'ANT': 'ANT',
    'VER': 'VER',
    'NOR': 'NOR',
    'PIA': 'PIA',
    'LEC': 'LEC',
    'HAM': 'HAM',
    'RUS': 'RUS',
    'LAW': 'LAW',
    'ALO': 'ALO',
    'STR': 'STR',
    'SAI': 'SAI',
    'ALB': 'ALB',
    'GAS': 'GAS',
    'COL': 'COL',
    'DOO': 'DOO',
    'OCO': 'OCO',
    'BEA': 'BEA',
    'TSU': 'TSU',
    'HAD': 'HAD',
    'LIN': 'LIN',
    'HUL': 'HUL',
    'BOR': 'BOR',
    'BOT': 'BOT',
    'POU': 'POU',
    'PER': 'PER',
}


def _get(url, timeout=15):
    """Make a GET request to the Jolpica API."""
    import requests as req
    try:
        resp = req.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"API request failed: {url} — {e}")
        return None


class Command(BaseCommand):
    help = 'Sync F1 race results and standings from Jolpica API (no FastF1 needed)'

    def add_arguments(self, parser):
        parser.add_argument('--season', type=int, default=2026, help='Season year')
        parser.add_argument('--round', type=int, default=None, help='Specific round to sync')
        parser.add_argument('--all-rounds', action='store_true', help='Sync all completed rounds')
        parser.add_argument('--standings-only', action='store_true', help='Only sync standings snapshots')

    def handle(self, *args, **options):
        from core.models import Race, Driver, SessionResult, StandingsSnapshot, Team
        from core.services.standings import StandingsService
        from core.services.scoring import PredictionScorer

        season = options['season']
        self.stdout.write(self.style.NOTICE(f'\n  Jolpica Sync — {season} Season\n'))

        scorer = PredictionScorer()
        standings_svc = StandingsService(season)

        if options['standings_only']:
            self._sync_standings_from_api(season)
            return

        if options['round']:
            # Sync a specific round
            rounds_to_sync = [options['round']]
        elif options['all_rounds']:
            # Sync all completed/active rounds
            now = timezone.now()
            all_races = Race.objects.filter(season=season).order_by('round_number')
            rounds_to_sync = [
                r.round_number for r in all_races
                if r.race_date < now or r.has_weekend_started
            ]
        else:
            # Default: sync active/completed rounds that lack race results
            now = timezone.now()
            rounds_to_sync = []
            all_races = Race.objects.filter(season=season).order_by('round_number')
            for race in all_races:
                if race.race_date < now or race.has_weekend_started:
                    has_results = SessionResult.objects.filter(race=race, session_type='race').exists()
                    if not has_results:
                        rounds_to_sync.append(race.round_number)

        self.stdout.write(f'  Rounds to sync: {rounds_to_sync or "none needed"}')

        total_results = 0
        for round_num in rounds_to_sync:
            try:
                race = Race.objects.get(season=season, round_number=round_num)
            except Race.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'  Round {round_num}: Race not found in DB — skipping'))
                continue

            self.stdout.write(f'\n  Round {round_num}: {race.name}')

            # Sync qualifying
            q_count = self._sync_session(season, round_num, race, 'qualifying')
            self.stdout.write(f'    Qualifying: {q_count} results')

            # Sync sprint (if applicable)
            if race.has_sprint:
                s_count = self._sync_sprint(season, round_num, race)
                self.stdout.write(f'    Sprint: {s_count} results')

            # Sync race results
            r_count = self._sync_session(season, round_num, race, 'race')
            self.stdout.write(f'    Race: {r_count} results')
            total_results += r_count

            # Mark race as completed if we got results
            if r_count > 0:
                race.status = 'completed'
                race.is_completed = True
                race.save(update_fields=['status', 'is_completed'])

            # Score predictions for this race
            try:
                for st in ['qualifying', 'sprint', 'race']:
                    scorer.score_race_predictions(race, st)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'    Scoring: {e}'))

            # Create standings snapshot
            try:
                standings_svc.create_standings_snapshot(round_num)
                self.stdout.write(f'    Snapshot: created')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'    Snapshot: {e}'))

        # Always sync current standings from API
        self.stdout.write('\n  Syncing current standings from Jolpica...')
        self._sync_standings_from_api(season)

        self.stdout.write(self.style.SUCCESS(f'\n  Done! {total_results} race results synced.\n'))

    def _sync_session(self, season, round_num, race, session_type):
        """Sync qualifying or race results from Jolpica API."""
        from core.models import Driver, SessionResult

        if session_type == 'qualifying':
            url = f'{JOLPICA_BASE}/{season}/{round_num}/qualifying.json'
            result_key = 'QualifyingResults'
        else:
            url = f'{JOLPICA_BASE}/{season}/{round_num}/results.json'
            result_key = 'Results'

        data = _get(url)
        if not data:
            return 0

        races = data.get('MRData', {}).get('RaceTable', {}).get('Races', [])
        if not races:
            return 0

        results = races[0].get(result_key, [])
        count = 0

        with transaction.atomic():
            for result in results:
                driver_code = result.get('Driver', {}).get('code', '')
                abbr = DRIVER_CODE_MAP.get(driver_code, driver_code)

                try:
                    driver = Driver.objects.get(abbreviation=abbr)
                except Driver.DoesNotExist:
                    # Try creating/updating the driver on the fly
                    driver_info = result.get('Driver', {})
                    logger.warning(f"Driver {abbr} not in DB, skipping")
                    continue

                position_str = result.get('position', result.get('positionText', ''))
                try:
                    position = int(position_str)
                except (ValueError, TypeError):
                    continue  # Skip DNQ/DNS

                if session_type == 'race':
                    points_str = result.get('points', '0')
                    try:
                        points = Decimal(str(float(points_str)))
                    except Exception:
                        points = Decimal('0')

                    grid_str = result.get('grid', None)
                    try:
                        grid = int(grid_str) if grid_str else None
                    except (ValueError, TypeError):
                        grid = None

                    status = result.get('status', 'Finished')
                    time_info = result.get('Time', {})
                    time_str = time_info.get('time', '') if time_info else ''

                    fl_info = result.get('FastestLap', {})
                    fl_rank = fl_info.get('rank', '99') if fl_info else '99'
                    is_fl = (fl_rank == '1')

                    result_data = {
                        'position': position,
                        'grid_position': grid,
                        'points': points,
                        'status': status,
                        'time': time_str,
                        'fastest_lap': is_fl,
                    }
                else:
                    # Qualifying
                    result_data = {
                        'position': position,
                        'points': Decimal('0'),
                        'status': 'Finished',
                        'q1_time': result.get('Q1', ''),
                        'q2_time': result.get('Q2', ''),
                        'q3_time': result.get('Q3', ''),
                    }

                SessionResult.objects.update_or_create(
                    race=race,
                    driver=driver,
                    session_type=session_type,
                    defaults=result_data,
                )
                count += 1

        return count

    def _sync_sprint(self, season, round_num, race):
        """Sync sprint race results from Jolpica API."""
        from core.models import Driver, SessionResult

        url = f'{JOLPICA_BASE}/{season}/{round_num}/sprint.json'
        data = _get(url)
        if not data:
            return 0

        races = data.get('MRData', {}).get('RaceTable', {}).get('Races', [])
        if not races:
            return 0

        results = races[0].get('SprintResults', [])
        count = 0

        with transaction.atomic():
            for result in results:
                driver_code = result.get('Driver', {}).get('code', '')
                abbr = DRIVER_CODE_MAP.get(driver_code, driver_code)

                try:
                    driver = Driver.objects.get(abbreviation=abbr)
                except Driver.DoesNotExist:
                    logger.warning(f"Sprint: Driver {abbr} not in DB")
                    continue

                position_str = result.get('position', '')
                try:
                    position = int(position_str)
                except (ValueError, TypeError):
                    continue

                points_str = result.get('points', '0')
                try:
                    points = Decimal(str(float(points_str)))
                except Exception:
                    points = Decimal('0')

                status = result.get('status', 'Finished')
                time_info = result.get('Time', {})
                time_str = time_info.get('time', '') if time_info else ''

                SessionResult.objects.update_or_create(
                    race=race,
                    driver=driver,
                    session_type='sprint',
                    defaults={
                        'position': position,
                        'points': points,
                        'status': status,
                        'time': time_str,
                    }
                )
                count += 1

        return count

    def _sync_standings_from_api(self, season):
        """Sync current championship standings snapshot from Jolpica API."""
        from core.models import Driver, Team, StandingsSnapshot

        # Driver standings
        url = f'{JOLPICA_BASE}/{season}/driverStandings.json'
        data = _get(url)
        if data:
            standings_table = data.get('MRData', {}).get('StandingsTable', {})
            standings_lists = standings_table.get('StandingsLists', [])
            if standings_lists:
                sl = standings_lists[0]
                round_num = int(sl.get('round', 0))
                driver_standings = sl.get('DriverStandings', [])

                with transaction.atomic():
                    StandingsSnapshot.objects.filter(
                        season=season, round_number=round_num, snapshot_type='driver'
                    ).delete()

                    for ds in driver_standings:
                        position = int(ds.get('position', 0))
                        points = Decimal(str(float(ds.get('points', '0'))))
                        wins = int(ds.get('wins', 0))
                        driver_code = ds.get('Driver', {}).get('code', '')
                        abbr = DRIVER_CODE_MAP.get(driver_code, driver_code)
                        constructor_id = ''
                        constructors = ds.get('Constructors', [])
                        if constructors:
                            constructor_id = constructors[0].get('constructorId', '')

                        try:
                            driver = Driver.objects.get(abbreviation=abbr)
                            team = Team.objects.filter(constructor_id=constructor_id).first()
                            if not team:
                                team = driver.current_team(season)
                            if not team:
                                continue

                            StandingsSnapshot.objects.create(
                                season=season,
                                round_number=round_num,
                                driver=driver,
                                team=team,
                                points=points,
                                position=position,
                                snapshot_type='driver',
                                wins=wins,
                            )
                        except Driver.DoesNotExist:
                            logger.warning(f"Standings: Driver {abbr} not found")

                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] {len(driver_standings)} driver standings (R{round_num})')
                )

        # Constructor standings
        url = f'{JOLPICA_BASE}/{season}/constructorStandings.json'
        data = _get(url)
        if data:
            standings_table = data.get('MRData', {}).get('StandingsTable', {})
            standings_lists = standings_table.get('StandingsLists', [])
            if standings_lists:
                sl = standings_lists[0]
                round_num = int(sl.get('round', 0))
                constructor_standings = sl.get('ConstructorStandings', [])

                with transaction.atomic():
                    StandingsSnapshot.objects.filter(
                        season=season, round_number=round_num, snapshot_type='constructor'
                    ).delete()

                    for cs in constructor_standings:
                        position = int(cs.get('position', 0))
                        points = Decimal(str(float(cs.get('points', '0'))))
                        wins = int(cs.get('wins', 0))
                        constructor_id = cs.get('Constructor', {}).get('constructorId', '')

                        try:
                            team = Team.objects.get(constructor_id=constructor_id)
                            StandingsSnapshot.objects.create(
                                season=season,
                                round_number=round_num,
                                driver=None,
                                team=team,
                                points=points,
                                position=position,
                                snapshot_type='constructor',
                                wins=wins,
                            )
                        except Team.DoesNotExist:
                            logger.warning(f"Standings: Team {constructor_id} not found")

                self.stdout.write(
                    self.style.SUCCESS(f'  [OK] {len(constructor_standings)} constructor standings (R{round_num})')
                )
