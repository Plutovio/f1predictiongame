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


def driver_detail(request, driver_id):
    """Individual driver profile page with analytics and race history."""
    from django.db.models import Sum
    from core.models import Race, SessionResult
    
    season = 2026
    driver = get_object_or_404(Driver, id=driver_id)
    standings_service = StandingsService(season)
    
    # 1. Driver current standing info
    driver_standings_list = standings_service.calculate_driver_standings()
    driver_standing = None
    for entry in driver_standings_list:
        if entry['driver'].id == driver.id:
            driver_standing = entry
            break
            
    # 2. Comprehensive career/season stats
    stats = standings_service.get_driver_stats(driver)
    
    # 3. Round-by-round points progression for single driver
    completed_races = Race.objects.filter(season=season, is_completed=True).order_by('round_number')
    labels = [f"R{r.round_number}" for r in completed_races]
    
    round_pts = {}
    for r in completed_races:
        pts = SessionResult.objects.filter(
            driver=driver,
            race=r,
            session_type__in=['race', 'sprint']
        ).aggregate(t=Sum('points'))['t'] or 0
        round_pts[r.round_number] = float(pts)
        
    cumulative = 0
    points_data = []
    for r in completed_races:
        cumulative += round_pts.get(r.round_number, 0.0)
        points_data.append(cumulative)
        
    progression_data = {
        'labels': labels,
        'datasets': [{
            'label': f"{driver.abbreviation} Points",
            'data': points_data,
            'borderColor': driver.current_team(season).color_primary if driver.current_team(season) else '#E10600',
            'backgroundColor': 'rgba(255, 255, 255, 0.01)',
            'borderWidth': 3,
            'pointRadius': 4
        }]
    }
    
    # 4. Detailed weekend-by-weekend results list
    weekend_stats = []
    qualifying_results = SessionResult.objects.filter(driver=driver, race__season=season, session_type='qualifying')
    sprint_results = SessionResult.objects.filter(driver=driver, race__season=season, session_type='sprint')
    race_results = SessionResult.objects.filter(driver=driver, race__season=season, session_type='race')
    
    for race in Race.objects.filter(season=season).order_by('round_number'):
        q_res = qualifying_results.filter(race=race).first()
        s_res = sprint_results.filter(race=race).first()
        r_res = race_results.filter(race=race).first()
        
        if not q_res and not s_res and not r_res:
            continue
            
        weekend_stats.append({
            'race': race,
            'quali_pos': q_res.position if q_res else '—',
            'sprint_pos': s_res.position if s_res else '—',
            'race_pos': r_res.position if r_res else '—',
            'points': float((s_res.points if s_res else 0) + (r_res.points if r_res else 0)),
            'status': r_res.status if r_res else '—',
            'fastest_lap': r_res.fastest_lap if r_res else False
        })
        
    context = {
        'driver': driver,
        'team': driver.current_team(season),
        'theme_team': driver.current_team(season),
        'standing': driver_standing,
        'stats': stats,
        'progression_data': json.dumps(progression_data),
        'weekend_stats': weekend_stats,
    }
    return render(request, 'standings/driver_detail.html', context)


def team_detail(request, team_id):
    """Individual constructor profile page with analytics and results history."""
    from django.db.models import Sum
    from core.models import Race, SessionResult
    
    season = 2026
    team = get_object_or_404(Team, id=team_id)
    standings_service = StandingsService(season)
    
    # 1. Constructor standing info
    constructor_standings_list = standings_service.calculate_constructor_standings()
    team_standing = None
    for entry in constructor_standings_list:
        if entry['team'].id == team.id:
            team_standing = entry
            break
            
    # 2. Get active drivers (deduplicated)
    active_drivers = DriverTeamHistory.objects.filter(
        team=team,
        season=season,
        is_active=True
    ).select_related('driver').order_by('-date_from')
    
    seen_drivers = set()
    drivers_list = []
    for entry in active_drivers:
        if entry.driver_id not in seen_drivers:
            seen_drivers.add(entry.driver_id)
            drivers_list.append(entry.driver)
    
    # 3. Round-by-round points progression for team
    completed_races = Race.objects.filter(season=season, is_completed=True).order_by('round_number')
    labels = [f"R{r.round_number}" for r in completed_races]
    
    driver_ids = [d.id for d in drivers_list]
    
    round_pts = {}
    for r in completed_races:
        pts = SessionResult.objects.filter(
            driver_id__in=driver_ids,
            race=r,
            session_type__in=['race', 'sprint']
        ).aggregate(t=Sum('points'))['t'] or 0
        round_pts[r.round_number] = float(pts)
        
    cumulative = 0
    points_data = []
    for r in completed_races:
        cumulative += round_pts.get(r.round_number, 0.0)
        points_data.append(cumulative)
        
    progression_data = {
        'labels': labels,
        'datasets': [{
            'label': f"{team.short_name} Points",
            'data': points_data,
            'borderColor': team.color_primary,
            'backgroundColor': 'rgba(255, 255, 255, 0.01)',
            'borderWidth': 3,
            'pointRadius': 4
        }]
    }
    
    # 4. Detailed weekend-by-weekend team results list
    weekend_stats = []
    for race in Race.objects.filter(season=season).order_by('round_number'):
        race_results = SessionResult.objects.filter(
            driver_id__in=driver_ids,
            race=race,
            session_type='race'
        ).select_related('driver')
        
        if not race_results.exists():
            continue
            
        drivers_results = []
        total_weekend_pts = 0
        has_any_result = False
        for d in drivers_list:
            res = race_results.filter(driver=d).first()
            if res:
                has_any_result = True
                sprint_pts = SessionResult.objects.filter(
                    driver=d,
                    race=race,
                    session_type='sprint'
                ).aggregate(t=Sum('points'))['t'] or 0
                
                pts = float(res.points + sprint_pts)
                total_weekend_pts += pts
                
                drivers_results.append({
                    'driver': d,
                    'pos': res.position,
                    'points': pts,
                    'status': res.status,
                    'fastest_lap': res.fastest_lap
                })
            else:
                drivers_results.append({
                    'driver': d,
                    'pos': None,
                    'points': 0.0,
                    'status': '—',
                    'fastest_lap': False
                })
                
        if not has_any_result:
            continue
            
        weekend_stats.append({
            'race': race,
            'results': drivers_results,
            'total_points': total_weekend_pts
        })
        
    context = {
        'team': team,
        'theme_team': team,
        'standing': team_standing,
        'drivers': drivers_list,
        'progression_data': json.dumps(progression_data),
        'weekend_stats': weekend_stats,
    }
    return render(request, 'standings/team_detail.html', context)
