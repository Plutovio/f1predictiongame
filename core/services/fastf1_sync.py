"""
F1 Predictor — FastF1 Data Synchronization Service

Handles all data fetching from FastF1 and the Jolpica API,
mapping external data into Django models.
"""
import logging
from datetime import datetime, date
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from django.db import transaction

from core.models import (
    Team, Driver, DriverTeamHistory, Race, SessionResult, StandingsSnapshot
)

logger = logging.getLogger(__name__)

# Lazy imports for optional heavy dependencies
fastf1 = None
requests = None


def _ensure_fastf1():
    """Lazy-load fastf1 and set up cache."""
    global fastf1
    if fastf1 is None:
        import importlib
        fastf1 = importlib.import_module('fastf1')
        try:
            import os
            cache_dir = getattr(settings, 'FASTF1_CACHE_DIR', './fastf1_cache')
            os.makedirs(cache_dir, exist_ok=True)
            fastf1.Cache.enable_cache(cache_dir)
        except Exception as e:
            logger.warning(f"FastF1 cache setup failed: {e}")
    return fastf1


def _ensure_requests():
    """Lazy-load requests."""
    global requests
    if requests is None:
        import importlib
        requests = importlib.import_module('requests')
    return requests


# 2026 team data for seeding
TEAMS_2026 = [
    {'name': 'Red Bull Racing', 'short_name': 'Red Bull', 'color_primary': '#3671C6', 'color_secondary': '#FFD700', 'constructor_id': 'red_bull'},
    {'name': 'McLaren', 'short_name': 'McLaren', 'color_primary': '#FF8000', 'color_secondary': '#47C7FC', 'constructor_id': 'mclaren'},
    {'name': 'Ferrari', 'short_name': 'Ferrari', 'color_primary': '#E8002D', 'color_secondary': '#FFEB3B', 'constructor_id': 'ferrari'},
    {'name': 'Mercedes-AMG Petronas', 'short_name': 'Mercedes', 'color_primary': '#27F4D2', 'color_secondary': '#000000', 'constructor_id': 'mercedes'},
    {'name': 'Aston Martin', 'short_name': 'Aston Martin', 'color_primary': '#229971', 'color_secondary': '#CEDC00', 'constructor_id': 'aston_martin'},
    {'name': 'Williams Racing', 'short_name': 'Williams', 'color_primary': '#64C4FF', 'color_secondary': '#012564', 'constructor_id': 'williams'},
    {'name': 'Alpine', 'short_name': 'Alpine', 'color_primary': '#FF87BC', 'color_secondary': '#0093CC', 'constructor_id': 'alpine'},
    {'name': 'Haas F1 Team', 'short_name': 'Haas', 'color_primary': '#B6BABD', 'color_secondary': '#E10600', 'constructor_id': 'haas'},
    {'name': 'Racing Bulls', 'short_name': 'Racing Bulls', 'color_primary': '#6692FF', 'color_secondary': '#FFFFFF', 'constructor_id': 'rb'},
    {'name': 'Audi', 'short_name': 'Audi', 'color_primary': '#F50537', 'color_secondary': '#000000', 'constructor_id': 'audi'},
    {'name': 'Cadillac F1 Team', 'short_name': 'Cadillac', 'color_primary': '#FFD700', 'color_secondary': '#1C1C1C', 'constructor_id': 'cadillac'},
]

# 2026 driver lineup
DRIVERS_2026 = [
    {'first_name': 'Max', 'last_name': 'Verstappen', 'abbreviation': 'VER', 'number': 1, 'country': 'Netherlands', 'country_code': 'NLD', 'team': 'Red Bull Racing'},
    {'first_name': 'Isack', 'last_name': 'Hadjar', 'abbreviation': 'HAD', 'number': 6, 'country': 'France', 'country_code': 'FRA', 'team': 'Red Bull Racing'},
    {'first_name': 'Lando', 'last_name': 'Norris', 'abbreviation': 'NOR', 'number': 4, 'country': 'United Kingdom', 'country_code': 'GBR', 'team': 'McLaren'},
    {'first_name': 'Oscar', 'last_name': 'Piastri', 'abbreviation': 'PIA', 'number': 81, 'country': 'Australia', 'country_code': 'AUS', 'team': 'McLaren'},
    {'first_name': 'Charles', 'last_name': 'Leclerc', 'abbreviation': 'LEC', 'number': 16, 'country': 'Monaco', 'country_code': 'MON', 'team': 'Ferrari'},
    {'first_name': 'Lewis', 'last_name': 'Hamilton', 'abbreviation': 'HAM', 'number': 44, 'country': 'United Kingdom', 'country_code': 'GBR', 'team': 'Ferrari'},
    {'first_name': 'George', 'last_name': 'Russell', 'abbreviation': 'RUS', 'number': 63, 'country': 'United Kingdom', 'country_code': 'GBR', 'team': 'Mercedes-AMG Petronas'},
    {'first_name': 'Kimi', 'last_name': 'Antonelli', 'abbreviation': 'ANT', 'number': 12, 'country': 'Italy', 'country_code': 'ITA', 'team': 'Mercedes-AMG Petronas'},
    {'first_name': 'Fernando', 'last_name': 'Alonso', 'abbreviation': 'ALO', 'number': 14, 'country': 'Spain', 'country_code': 'ESP', 'team': 'Aston Martin'},
    {'first_name': 'Lance', 'last_name': 'Stroll', 'abbreviation': 'STR', 'number': 18, 'country': 'Canada', 'country_code': 'CAN', 'team': 'Aston Martin'},
    {'first_name': 'Alex', 'last_name': 'Albon', 'abbreviation': 'ALB', 'number': 23, 'country': 'Thailand', 'country_code': 'THA', 'team': 'Williams Racing'},
    {'first_name': 'Carlos', 'last_name': 'Sainz', 'abbreviation': 'SAI', 'number': 55, 'country': 'Spain', 'country_code': 'ESP', 'team': 'Williams Racing'},
    {'first_name': 'Pierre', 'last_name': 'Gasly', 'abbreviation': 'GAS', 'number': 10, 'country': 'France', 'country_code': 'FRA', 'team': 'Alpine'},
    {'first_name': 'Franco', 'last_name': 'Colapinto', 'abbreviation': 'COL', 'number': 43, 'country': 'Argentina', 'country_code': 'ARG', 'team': 'Alpine'},
    {'first_name': 'Esteban', 'last_name': 'Ocon', 'abbreviation': 'OCO', 'number': 31, 'country': 'France', 'country_code': 'FRA', 'team': 'Haas F1 Team'},
    {'first_name': 'Oliver', 'last_name': 'Bearman', 'abbreviation': 'BEA', 'number': 87, 'country': 'United Kingdom', 'country_code': 'GBR', 'team': 'Haas F1 Team'},
    {'first_name': 'Liam', 'last_name': 'Lawson', 'abbreviation': 'LAW', 'number': 30, 'country': 'New Zealand', 'country_code': 'NZL', 'team': 'Racing Bulls'},
    {'first_name': 'Arvid', 'last_name': 'Lindblad', 'abbreviation': 'LIN', 'number': 45, 'country': 'United Kingdom', 'country_code': 'GBR', 'team': 'Racing Bulls'},
    {'first_name': 'Nico', 'last_name': 'Hülkenberg', 'abbreviation': 'HUL', 'number': 27, 'country': 'Germany', 'country_code': 'DEU', 'team': 'Audi'},
    {'first_name': 'Gabriel', 'last_name': 'Bortoleto', 'abbreviation': 'BOR', 'number': 5, 'country': 'Brazil', 'country_code': 'BRA', 'team': 'Audi'},
    {'first_name': 'Valtteri', 'last_name': 'Bottas', 'abbreviation': 'BOT', 'number': 77, 'country': 'Finland', 'country_code': 'FIN', 'team': 'Cadillac F1 Team'},
    {'first_name': 'Sergio', 'last_name': 'Pérez', 'abbreviation': 'PER', 'number': 11, 'country': 'Mexico', 'country_code': 'MEX', 'team': 'Cadillac F1 Team'},
]


class FastF1SyncService:
    """Service for syncing F1 data from FastF1 and Jolpica API."""

    JOLPICA_BASE = 'https://api.jolpi.ca/ergast/f1'

    def __init__(self, season=None):
        self.season = season or getattr(settings, 'F1_CURRENT_SEASON', 2026)

    # ──────────────────────────────────────────────
    # SEED DATA
    # ──────────────────────────────────────────────

    @transaction.atomic
    def seed_teams_and_drivers(self):
        """Seed initial team and driver data for 2026."""
        logger.info("Seeding 2026 teams...")
        teams = {}
        for t in TEAMS_2026:
            team, created = Team.objects.update_or_create(
                name=t['name'],
                defaults={
                    'short_name': t['short_name'],
                    'color_primary': t['color_primary'],
                    'color_secondary': t['color_secondary'],
                    'constructor_id': t['constructor_id'],
                    'is_active': True,
                }
            )
            teams[t['name']] = team
            status = "Created" if created else "Updated"
            logger.info(f"  {status}: {team.name}")

        logger.info("Seeding 2026 drivers...")
        for d in DRIVERS_2026:
            driver, created = Driver.objects.update_or_create(
                abbreviation=d['abbreviation'],
                defaults={
                    'first_name': d['first_name'],
                    'last_name': d['last_name'],
                    'number': d['number'],
                    'country': d['country'],
                    'country_code': d.get('country_code', ''),
                    'is_reserve': False,
                }
            )
            # Create team assignment
            team = teams.get(d['team'])
            if team:
                DriverTeamHistory.objects.update_or_create(
                    driver=driver,
                    team=team,
                    season=self.season,
                    date_from=date(self.season, 1, 1),
                    defaults={'is_active': True, 'date_to': None}
                )
            status = "Created" if created else "Updated"
            logger.info(f"  {status}: {driver.full_name} → {d['team']}")

        return len(TEAMS_2026), len(DRIVERS_2026)

    # ──────────────────────────────────────────────
    # SCHEDULE SYNC
    # ──────────────────────────────────────────────

    @transaction.atomic
    def sync_schedule(self):
        """Sync season schedule from FastF1."""
        ff1 = _ensure_fastf1()
        logger.info(f"Syncing {self.season} schedule from FastF1...")
        try:
            schedule = ff1.get_event_schedule(self.season)
            races_only = schedule[schedule['RoundNumber'] > 0]
        except Exception as e:
            logger.error(f"FastF1 schedule fetch failed: {e}")
            return 0

        count = 0
        for _, event in races_only.iterrows():
            round_num = int(event['RoundNumber'])
            event_format = event.get('EventFormat', 'conventional')
            has_sprint = 'sprint' in event_format

            # Parse session dates
            def parse_date(val):
                if val is not None and not (hasattr(val, 'isnull') and val.isnull()):
                    try:
                        if hasattr(val, 'to_pydatetime'):
                            dt = val.to_pydatetime()
                        else:
                            dt = val
                        if timezone.is_naive(dt):
                            dt = timezone.make_aware(dt)
                        return dt
                    except Exception:
                        pass
                return None

            race_data = {
                'name': str(event.get('EventName', f'Round {round_num}')),
                'official_name': str(event.get('OfficialEventName', '')),
                'country': str(event.get('Country', '')),
                'city': str(event.get('Location', '')),
                'circuit_name': str(event.get('Location', '')),
                'race_date': parse_date(event.get('Session5Date')) or parse_date(event.get('EventDate')),
                'qualifying_date': parse_date(event.get('Session4Date') if not has_sprint else event.get('Session3Date')),
                'fp1_date': parse_date(event.get('Session1Date')),
                'fp2_date': parse_date(event.get('Session2Date') if not has_sprint else None),
                'fp3_date': parse_date(event.get('Session3Date') if not has_sprint else None),
                'sprint_qualifying_date': parse_date(event.get('Session2Date') if has_sprint else None),
                'sprint_date': parse_date(event.get('Session4Date') if has_sprint else None),
                'has_sprint': has_sprint,
                'fastf1_event_name': str(event.get('EventName', '')),
            }

            # Check if race has happened
            if race_data['race_date'] and race_data['race_date'] < timezone.now():
                race_data['status'] = 'completed'
                race_data['is_completed'] = True
            else:
                race_data['status'] = 'upcoming'
                race_data['is_completed'] = False

            race, created = Race.objects.update_or_create(
                season=self.season,
                round_number=round_num,
                defaults=race_data,
            )
            count += 1
            status = "Created" if created else "Updated"
            logger.info(f"  {status}: R{round_num} {race.name}")

        logger.info(f"Schedule sync complete: {count} races")
        return count

    # ──────────────────────────────────────────────
    # RESULTS SYNC
    # ──────────────────────────────────────────────

    def sync_session_results(self, race, session_type, force=False):
        """Sync results for a specific session from FastF1."""
        session_map = {
            'fp1': 'FP1',
            'fp2': 'FP2',
            'fp3': 'FP3',
            'sprint_qualifying': 'SQ',
            'qualifying': 'Q',
            'sprint': 'S',
            'race': 'R',
        }
        ff1_session_id = session_map.get(session_type)
        if not ff1_session_id:
            logger.error(f"Unknown session type: {session_type}")
            return 0

        # Skip sprint for non-sprint weekends
        if session_type == 'sprint' and not race.has_sprint:
            return 0

        # Optimization: Skip session if its scheduled date is in the future
        session_date_map = {
            'fp1': race.fp1_date,
            'fp2': race.fp2_date,
            'fp3': race.fp3_date,
            'sprint_qualifying': race.sprint_qualifying_date,
            'qualifying': race.qualifying_date,
            'sprint': race.sprint_date,
            'race': race.race_date,
        }
        session_date = session_date_map.get(session_type)
        if not force and session_date and timezone.now() < session_date:
            logger.info(f"Skipping {session_type} for {race.name} because session date {session_date} is in the future.")
            return 0

        # Optimization: Skip if we already have 19+ results for this session in the DB
        if not force:
            existing_count = SessionResult.objects.filter(race=race, session_type=session_type).count()
            if existing_count >= 19:
                logger.info(f"Skipping {session_type} for {race.name} because {existing_count} results already exist in DB.")
                return 0

        try:
            ff1 = _ensure_fastf1()
            logger.info(f"Loading {session_type} results for {race.name}...")
            session = ff1.get_session(self.season, race.round_number, ff1_session_id)
            # Optimization: only load laps if we need to calculate positions from laps (practices and sprint qualifying)
            needs_lap_calc = session_type in ('fp1', 'fp2', 'fp3', 'sprint_qualifying')
            session.load(telemetry=False, weather=False, messages=False, laps=needs_lap_calc)
            results = session.results
        except Exception as e:
            logger.warning(f"Could not load {session_type} for {race.name}: {e}")
            return 0

        if results is None or results.empty:
            logger.info(f"No results available for {race.name} {session_type}")
            return 0

        # Check if we need to calculate positions from laps (e.g. for practices or if positions are all NaN)
        needs_lap_calc = session_type in ('fp1', 'fp2', 'fp3', 'sprint_qualifying')
        
        if not needs_lap_calc:
            all_pos_nan = True
            for _, row in results.iterrows():
                pos = row.get('Position')
                if pos is not None and str(pos) != 'nan':
                    all_pos_nan = False
                    break
            if all_pos_nan:
                # We can only calculate from laps if we actually loaded them (FP sessions and sprint qualifying)
                laps_actually_loaded = session_type in ('fp1', 'fp2', 'fp3', 'sprint_qualifying')
                if laps_actually_loaded:
                    needs_lap_calc = True

        driver_results = []
        if needs_lap_calc and session.laps is not None and not session.laps.empty:
            import pandas as pd
            for _, row in results.iterrows():
                abbr = str(row.get('Abbreviation', '')).strip()
                if not abbr:
                    continue
                try:
                    driver_laps = session.laps.pick_drivers(abbr)
                    laps_count = len(driver_laps)
                    fl = driver_laps.pick_fastest()
                    best_time = fl['LapTime'] if fl is not None and not pd.isnull(fl['LapTime']) else None
                except Exception:
                    best_time = None
                    laps_count = 0
                
                driver_results.append({
                    'row': row,
                    'abbr': abbr,
                    'best_time': best_time,
                    'laps_count': laps_count,
                })
            
            # Sort by best_time, putting NaT/None at the end
            driver_results.sort(key=lambda x: (x['best_time'] is None, x['best_time']))
            
            # Assign calculated positions
            for idx, item in enumerate(driver_results, 1):
                item['position'] = idx
        else:
            # Standard path: use official Position
            for _, row in results.iterrows():
                abbr = str(row.get('Abbreviation', '')).strip()
                if not abbr:
                    continue
                pos = row.get('Position')
                if pos is None or str(pos) == 'nan':
                    continue
                
                laps_val = row.get('Laps')
                try:
                    laps_count = int(float(laps_val)) if laps_val is not None and str(laps_val) != 'nan' else 0
                except Exception:
                    laps_count = 0

                driver_results.append({
                    'row': row,
                    'abbr': abbr,
                    'position': int(float(pos)),
                    'best_time': None,
                    'laps_count': laps_count,
                })

        count = 0
        with transaction.atomic():
            for item in driver_results:
                abbr = item['abbr']
                row = item['row']
                position = item['position']
                laps_completed = item['laps_count']
                
                try:
                    driver = Driver.objects.get(abbreviation=abbr)
                except Driver.DoesNotExist:
                    logger.warning(f"Driver {abbr} not found in database, skipping")
                    continue

                grid = row.get('GridPosition')
                if grid is not None and str(grid) != 'nan':
                    grid = int(float(grid))
                    if grid <= 0:
                        grid = None
                else:
                    grid = None

                points = row.get('Points', 0)
                if str(points) == 'nan':
                    points = 0
                points = Decimal(str(float(points)))

                status = str(row.get('Status', 'Finished'))
                
                # For practice, use calculated best_time if available, otherwise fallback
                if item.get('best_time') is not None:
                    time_str = str(item['best_time'])
                else:
                    time_str = ''
                    if 'Time' in row and row['Time'] is not None and str(row['Time']) != 'NaT':
                        time_str = str(row['Time'])

                result_data = {
                    'position': position,
                    'grid_position': grid,
                    'points': points,
                    'status': status,
                    'time': time_str,
                    'fastest_lap': position == 1 if needs_lap_calc else bool(row.get('FastestLap', False)),
                    'laps_completed': laps_completed,
                }

                # Add qualifying times if applicable
                if session_type == 'qualifying':
                    for q in ['Q1', 'Q2', 'Q3']:
                        val = row.get(q)
                        if val is not None and str(val) not in ('NaT', 'nan', ''):
                            result_data[f'{q.lower()}_time'] = str(val)

                SessionResult.objects.update_or_create(
                    race=race,
                    driver=driver,
                    session_type=session_type,
                    defaults=result_data,
                )
                count += 1

        logger.info(f"  Synced {count} {session_type} results for {race.name}")
        return count

    def sync_race_all_sessions(self, race, force=False):
        """Sync all session results for a race."""
        total = 0
        total += self.sync_session_results(race, 'fp1', force=force)
        if race.has_sprint:
            total += self.sync_session_results(race, 'sprint_qualifying', force=force)
            total += self.sync_session_results(race, 'sprint', force=force)
        else:
            total += self.sync_session_results(race, 'fp2', force=force)
            total += self.sync_session_results(race, 'fp3', force=force)
        total += self.sync_session_results(race, 'qualifying', force=force)
        total += self.sync_session_results(race, 'race', force=force)
        return total

    def sync_latest_results(self):
        """Find the most recently completed race and sync its results."""
        now = timezone.now()
        recent_races = Race.objects.filter(
            season=self.season,
            race_date__lt=now,
        ).order_by('-race_date')

        total = 0
        for race in recent_races:
            # Only sync if we don't have race results yet
            has_race_results = SessionResult.objects.filter(
                race=race, session_type='race'
            ).exists()

            if not has_race_results:
                synced = self.sync_race_all_sessions(race)
                if synced > 0:
                    race.status = 'completed'
                    race.is_completed = True
                    race.save()
                    total += synced

        return total

    # ──────────────────────────────────────────────
    # STANDINGS SYNC
    # ──────────────────────────────────────────────

    def sync_standings(self):
        """Sync championship standings from Jolpica API and calculate snapshots."""
        logger.info(f"Syncing {self.season} standings...")
        self._sync_driver_standings()
        self._sync_constructor_standings()
        logger.info("Standings sync complete")

    def _sync_driver_standings(self):
        """Fetch driver standings from Jolpica API."""
        req = _ensure_requests()
        try:
            resp = req.get(
                f'{self.JOLPICA_BASE}/{self.season}/driverStandings.json',
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            standings_list = (
                data.get('MRData', {})
                .get('StandingsTable', {})
                .get('StandingsLists', [])
            )
            if not standings_list:
                logger.warning("No driver standings data found")
                return

            standings_data = standings_list[0]
            round_num = int(standings_data.get('round', 0))
            driver_standings = standings_data.get('DriverStandings', [])

            with transaction.atomic():
                # Clear existing snapshots for this round
                StandingsSnapshot.objects.filter(
                    season=self.season,
                    round_number=round_num,
                    snapshot_type='driver'
                ).delete()

                for ds in driver_standings:
                    position = int(ds.get('position', 0))
                    points = Decimal(ds.get('points', '0'))
                    wins = int(ds.get('wins', 0))

                    driver_info = ds.get('Driver', {})
                    driver_code = driver_info.get('code', '')

                    constructor_info = ds.get('Constructors', [{}])[0] if ds.get('Constructors') else {}
                    constructor_id = constructor_info.get('constructorId', '')

                    try:
                        driver = Driver.objects.get(abbreviation=driver_code)
                        team = Team.objects.filter(constructor_id=constructor_id).first()
                        if not team:
                            team = driver.current_team(self.season)
                        if not team:
                            continue

                        StandingsSnapshot.objects.create(
                            season=self.season,
                            round_number=round_num,
                            driver=driver,
                            team=team,
                            points=points,
                            position=position,
                            snapshot_type='driver',
                            wins=wins,
                        )
                    except Driver.DoesNotExist:
                        logger.warning(f"Driver {driver_code} not found for standings")

            logger.info(f"  Synced {len(driver_standings)} driver standings (R{round_num})")

        except Exception as e:
            logger.error(f"Driver standings sync error: {e}")

    def _sync_constructor_standings(self):
        """Fetch constructor standings from Jolpica API."""
        req = _ensure_requests()
        try:
            resp = req.get(
                f'{self.JOLPICA_BASE}/{self.season}/constructorStandings.json',
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()

            standings_list = (
                data.get('MRData', {})
                .get('StandingsTable', {})
                .get('StandingsLists', [])
            )
            if not standings_list:
                logger.warning("No constructor standings data found")
                return

            standings_data = standings_list[0]
            round_num = int(standings_data.get('round', 0))
            constructor_standings = standings_data.get('ConstructorStandings', [])

            with transaction.atomic():
                StandingsSnapshot.objects.filter(
                    season=self.season,
                    round_number=round_num,
                    snapshot_type='constructor'
                ).delete()

                for cs in constructor_standings:
                    position = int(cs.get('position', 0))
                    points = Decimal(cs.get('points', '0'))
                    wins = int(cs.get('wins', 0))

                    constructor_info = cs.get('Constructor', {})
                    constructor_id = constructor_info.get('constructorId', '')

                    try:
                        team = Team.objects.get(constructor_id=constructor_id)
                        StandingsSnapshot.objects.create(
                            season=self.season,
                            round_number=round_num,
                            driver=None,
                            team=team,
                            points=points,
                            position=position,
                            snapshot_type='constructor',
                            wins=wins,
                        )
                    except Team.DoesNotExist:
                        logger.warning(f"Team {constructor_id} not found for standings")

            logger.info(f"  Synced {len(constructor_standings)} constructor standings (R{round_num})")

        except Exception as e:
            logger.error(f"Constructor standings sync error: {e}")

    # ──────────────────────────────────────────────
    # DRIVER IMAGES SYNC
    # ──────────────────────────────────────────────

    def sync_driver_headshots(self):
        """Try to get driver headshot URLs from a FastF1 session."""
        try:
            # Load results from any completed session to get headshot URLs
            latest_race = Race.objects.filter(
                season=self.season,
                is_completed=True
            ).order_by('-round_number').first()

            if not latest_race:
                logger.info("No completed races to get headshots from")
                return

            ff1 = _ensure_fastf1()
            session = ff1.get_session(self.season, latest_race.round_number, 'R')
            session.load(telemetry=False, weather=False, messages=False, laps=False)

            for _, row in session.results.iterrows():
                abbr = str(row.get('Abbreviation', '')).strip()
                headshot = str(row.get('HeadshotUrl', '')).strip()
                if abbr and headshot and headshot != 'nan':
                    Driver.objects.filter(abbreviation=abbr).update(
                        headshot_url=headshot
                    )

            logger.info("Driver headshots synced")
        except Exception as e:
            logger.warning(f"Headshot sync failed: {e}")



