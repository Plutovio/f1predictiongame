"""
F1 Predictor — Standings Calculation Service

Calculates driver and constructor standings from session results
and creates snapshots for progression tracking.
"""
import logging
from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Count, Q

from core.models import (
    Driver, Team, Race, SessionResult, StandingsSnapshot, DriverTeamHistory
)

logger = logging.getLogger(__name__)


class StandingsService:
    """Calculate and manage championship standings."""

    def __init__(self, season=2026):
        self.season = season

    def calculate_driver_standings(self, up_to_round=None):
        """Calculate driver championship standings from race results up to an optional round."""
        drivers = Driver.objects.filter(
            team_history__season=self.season,
        ).distinct()

        standings = []
        for driver in drivers:
            results_filter = Q(
                driver=driver,
                race__season=self.season,
                session_type__in=['race', 'sprint'],
            )
            if up_to_round is not None:
                results_filter &= Q(race__round_number__lte=up_to_round)

            total_points = SessionResult.objects.filter(results_filter).aggregate(total=Sum('points'))['total'] or Decimal('0')

            wins_filter = Q(
                driver=driver,
                race__season=self.season,
                session_type='race',
                position=1,
            )
            if up_to_round is not None:
                wins_filter &= Q(race__round_number__lte=up_to_round)

            wins = SessionResult.objects.filter(wins_filter).count()

            podiums_filter = Q(
                driver=driver,
                race__season=self.season,
                session_type='race',
                position__lte=3,
            )
            if up_to_round is not None:
                podiums_filter &= Q(race__round_number__lte=up_to_round)

            podiums = SessionResult.objects.filter(podiums_filter).count()

            team = driver.current_team(self.season)

            standings.append({
                'driver': driver,
                'team': team,
                'points': total_points,
                'wins': wins,
                'podiums': podiums,
            })

        # Sort by points (desc), then wins (desc)
        standings.sort(key=lambda x: (-x['points'], -x['wins']))

        # Add positions
        for i, entry in enumerate(standings, 1):
            entry['position'] = i

        return standings

    def calculate_constructor_standings(self, up_to_round=None):
        """Calculate constructor championship standings up to an optional round."""
        teams = Team.objects.filter(is_active=True)

        standings = []
        for team in teams:
            # Get all drivers who raced for this team this season
            driver_ids = DriverTeamHistory.objects.filter(
                team=team,
                season=self.season,
            ).values_list('driver_id', flat=True)

            results_filter = Q(
                driver_id__in=driver_ids,
                race__season=self.season,
                session_type__in=['race', 'sprint'],
            )
            if up_to_round is not None:
                results_filter &= Q(race__round_number__lte=up_to_round)

            total_points = SessionResult.objects.filter(results_filter).aggregate(total=Sum('points'))['total'] or Decimal('0')

            wins_filter = Q(
                driver_id__in=driver_ids,
                race__season=self.season,
                session_type='race',
                position=1,
            )
            if up_to_round is not None:
                wins_filter &= Q(race__round_number__lte=up_to_round)

            wins = SessionResult.objects.filter(wins_filter).count()

            podiums_filter = Q(
                driver_id__in=driver_ids,
                race__season=self.season,
                session_type='race',
                position__lte=3,
            )
            if up_to_round is not None:
                podiums_filter &= Q(race__round_number__lte=up_to_round)

            podiums = SessionResult.objects.filter(podiums_filter).count()

            standings.append({
                'team': team,
                'points': total_points,
                'wins': wins,
                'podiums': podiums,
                'drivers': list(Driver.objects.filter(id__in=driver_ids)),
            })

        standings.sort(key=lambda x: (-x['points'], -x['wins']))

        for i, entry in enumerate(standings, 1):
            entry['position'] = i

        return standings

    @transaction.atomic
    def create_standings_snapshot(self, round_number):
        """Create a standings snapshot after a specific round with cumulative points."""
        # Driver standings cumulative up to this round
        driver_standings = self.calculate_driver_standings(up_to_round=round_number)
        for entry in driver_standings:
            if entry['team']:
                StandingsSnapshot.objects.update_or_create(
                    season=self.season,
                    round_number=round_number,
                    driver=entry['driver'],
                    snapshot_type='driver',
                    defaults={
                        'team': entry['team'],
                        'points': entry['points'],
                        'position': entry['position'],
                        'wins': entry['wins'],
                        'podiums': entry['podiums'],
                    }
                )

        # Constructor standings cumulative up to this round
        constructor_standings = self.calculate_constructor_standings(up_to_round=round_number)
        for entry in constructor_standings:
            StandingsSnapshot.objects.update_or_create(
                season=self.season,
                round_number=round_number,
                driver=None,
                team=entry['team'],
                snapshot_type='constructor',
                defaults={
                    'points': entry['points'],
                    'position': entry['position'],
                    'wins': entry['wins'],
                    'podiums': entry['podiums'],
                }
            )

        logger.info(f"Created standings snapshot for R{round_number}")

    def get_points_progression(self, snapshot_type='driver', limit=10):
        """Get points progression data for charts, selecting the top entities based on points."""
        snapshots = StandingsSnapshot.objects.filter(
            season=self.season,
            snapshot_type=snapshot_type,
        ).order_by('round_number')

        if not snapshots.exists():
            return {'labels': [], 'datasets': []}

        # Get rounds
        rounds = sorted(set(snapshots.values_list('round_number', flat=True)))

        # Find the latest round with non-zero points to determine the top entities
        latest_round = snapshots.filter(points__gt=0).order_by('-round_number').values_list('round_number', flat=True).first()
        if not latest_round:
            latest_round = max(rounds) if rounds else 1

        if snapshot_type == 'driver':
            # Get top N drivers by standings at latest_round
            top_entities = snapshots.filter(
                round_number=latest_round
            ).order_by('position')[:limit]

            datasets = []
            for entry in top_entities:
                driver = entry.driver
                team = entry.team
                data = []
                for r in rounds:
                    snap = snapshots.filter(
                        round_number=r, driver=driver
                    ).first()
                    data.append(float(snap.points) if snap else 0)

                datasets.append({
                    'label': driver.abbreviation,
                    'data': data,
                    'borderColor': team.color_primary if team else '#FFFFFF',
                    'backgroundColor': f'{team.color_primary}33' if team else '#FFFFFF33',
                })
        else:
            # Get top N teams by standings at latest_round
            top_entities = snapshots.filter(
                round_number=latest_round
            ).order_by('position')[:limit]

            datasets = []
            for entry in top_entities:
                team = entry.team
                data = []
                for r in rounds:
                    snap = snapshots.filter(
                        round_number=r, team=team, driver__isnull=True
                    ).first()
                    data.append(float(snap.points) if snap else 0)

                datasets.append({
                    'label': team.short_name,
                    'data': data,
                    'borderColor': team.color_primary,
                    'backgroundColor': f'{team.color_primary}33',
                })

        return {
            'labels': [f'R{r}' for r in rounds],
            'datasets': datasets,
        }

    def get_driver_stats(self, driver):
        """Get comprehensive stats for a specific driver."""
        results = SessionResult.objects.filter(
            driver=driver,
            race__season=self.season,
        )

        race_results = results.filter(session_type='race')
        quali_results = results.filter(session_type='qualifying')

        stats = {
            'races': race_results.count(),
            'wins': race_results.filter(position=1).count(),
            'podiums': race_results.filter(position__lte=3).count(),
            'points': results.filter(session_type__in=['race', 'sprint']).aggregate(t=Sum('points'))['t'] or 0,
            'dnfs': race_results.exclude(
                status__in=['Finished', '+1 Lap', '+2 Laps', '+3 Laps']
            ).count(),
            'best_finish': race_results.order_by('position').values_list(
                'position', flat=True
            ).first() or '—',
            'avg_finish': 0,
            'avg_quali': 0,
            'fastest_laps': race_results.filter(fastest_lap=True).count(),
        }

        # Average finish
        finishes = race_results.filter(
            status__in=['Finished', '+1 Lap', '+2 Laps', '+3 Laps']
        ).values_list('position', flat=True)
        if finishes:
            stats['avg_finish'] = round(sum(finishes) / len(finishes), 1)

        # Average qualifying
        quali_positions = quali_results.values_list('position', flat=True)
        if quali_positions:
            stats['avg_quali'] = round(sum(quali_positions) / len(quali_positions), 1)

        # Recent form (last 5 races)
        recent = race_results.order_by('-race__round_number')[:5]
        stats['recent_form'] = [
            {'round': r.race.round_number, 'position': r.position, 'points': float(r.points)}
            for r in recent
        ]

        return stats
