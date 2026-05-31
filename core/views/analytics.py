"""
F1 Predictor — Analytics Views
"""
import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q

from core.models import Race, StandingsSnapshot, Team
from core.services.standings import StandingsService


@login_required
def analytics(request):
    """Analytics dashboard focusing purely on Formula 1 racing statistics."""
    season = 2026
    standings_service = StandingsService(season)

    # 1. Points progression data for drivers and constructors
    driver_progression = standings_service.get_points_progression('driver', limit=10)
    constructor_progression = standings_service.get_points_progression('constructor', limit=11)

    # 2. Driver Stats for Wins & Podiums Chart
    driver_standings = standings_service.calculate_driver_standings()
    top_drivers = driver_standings[:10]
    
    wins_podiums_data = {
        'labels': [d['driver'].abbreviation for d in top_drivers],
        'wins': [d['wins'] for d in top_drivers],
        'podiums': [d['podiums'] for d in top_drivers],
    }

    # 3. Constructor Points Distribution Chart
    constructor_standings = standings_service.calculate_constructor_standings()
    constructor_dist_data = {
        'labels': [t['team'].short_name for t in constructor_standings],
        'points': [float(t['points']) for t in constructor_standings],
        'colors': [t['team'].color_primary for t in constructor_standings],
    }

    # 4. Detailed tables stats
    # Prepare driver stats from standings
    driver_stats_list = []
    for entry in driver_standings:
        stats = standings_service.get_driver_stats(entry['driver'])
        driver_stats_list.append({
            'driver': entry['driver'],
            'team': entry['team'],
            'points': entry['points'],
            'wins': entry['wins'],
            'podiums': entry['podiums'],
            'avg_finish': stats.get('avg_finish', '—'),
            'avg_quali': stats.get('avg_quali', '—'),
            'dnfs': stats.get('dnfs', 0),
            'fastest_laps': stats.get('fastest_laps', 0),
        })

    # Summary metrics for header
    total_races = Race.objects.filter(season=season).count()
    completed_races = Race.objects.filter(season=season, is_completed=True).count()
    
    championship_leader = driver_standings[0]['driver'].full_name if driver_standings else 'TBD'
    constructor_leader = constructor_standings[0]['team'].name if constructor_standings else 'TBD'
    
    most_wins_val = 0
    most_wins_driver = 'TBD'
    for entry in driver_standings:
        if entry['wins'] > most_wins_val:
            most_wins_val = entry['wins']
            most_wins_driver = entry['driver'].full_name
            
    stats_summary = {
        'total_races': total_races,
        'completed_races': completed_races,
        'leader': championship_leader,
        'constructor_leader': constructor_leader,
        'most_wins': f"{most_wins_driver} ({most_wins_val} wins)" if most_wins_val > 0 else 'TBD',
    }

    context = {
        'driver_progression': json.dumps(driver_progression),
        'constructor_progression': json.dumps(constructor_progression),
        'wins_podiums_data': json.dumps(wins_podiums_data),
        'constructor_dist_data': json.dumps(constructor_dist_data),
        'driver_stats': driver_stats_list,
        'constructor_standings': constructor_standings,
        'stats_summary': stats_summary,
    }
    return render(request, 'analytics/index.html', context)
