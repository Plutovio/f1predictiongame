"""
F1 Predictor — Standings Views
"""
import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from core.models import Driver, Team, StandingsSnapshot, DriverTeamHistory
from core.services.standings import StandingsService


def driver_standings(request):
    """Driver championship standings page."""
    season = 2026
    standings_service = StandingsService(season)
    standings = standings_service.calculate_driver_standings()

    # Get team filter
    team_filter = request.GET.get('team', '')
    search = request.GET.get('search', '') or request.GET.get('q', '')

    if team_filter:
        standings = [s for s in standings if s['team'] and s['team'].short_name == team_filter]

    if search:
        search_lower = search.lower()
        standings = [
            s for s in standings
            if search_lower in s['driver'].full_name.lower()
            or search_lower in s['driver'].abbreviation.lower()
        ]

    # Add extra stats for each driver
    for entry in standings:
        stats = standings_service.get_driver_stats(entry['driver'])
        entry.update(stats)
        entry['team_obj'] = entry['team']

    # Points progression chart data
    progression = standings_service.get_points_progression('driver', limit=10)

    teams = Team.objects.filter(is_active=True).order_by('name')

    # Handle HTMX partial requests
    if request.headers.get('HX-Request'):
        return render(request, 'partials/driver_search_results.html', {
            'standings': standings,
        })

    context = {
        'standings': standings,
        'teams': teams,
        'team_filter': team_filter,
        'search': search,
        'progression_data': json.dumps(progression),
    }
    return render(request, 'standings/drivers.html', context)


def constructor_standings(request):
    """Constructor championship standings page."""
    season = 2026
    standings_service = StandingsService(season)
    standings = standings_service.calculate_constructor_standings()

    # Points progression chart data
    progression = standings_service.get_points_progression('constructor', limit=11)

    context = {
        'standings': standings,
        'progression_data': json.dumps(progression),
    }
    return render(request, 'standings/constructors.html', context)
