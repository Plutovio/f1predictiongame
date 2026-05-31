"""
F1 Predictor — Race Views
"""
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from core.models import Race, SessionResult, Driver


def race_calendar(request):
    """Race calendar page showing all races in the season."""
    season = 2026
    now = timezone.now()
    races = Race.objects.filter(season=season).order_by('round_number')

    # Find the next race
    next_race = races.filter(race_date__gt=now).first()

    context = {
        'races': races,
        'next_race': next_race,
        'now': now,
    }
    return render(request, 'races/calendar.html', context)


def race_detail(request, race_id):
    """Individual race weekend page with results, schedule, weather."""
    race = get_object_or_404(Race, id=race_id)

    # Get results for each session
    qualifying_results = SessionResult.objects.filter(
        race=race, session_type='qualifying'
    ).order_by('position').select_related('driver')

    sprint_results = SessionResult.objects.filter(
        race=race, session_type='sprint'
    ).order_by('position').select_related('driver') if race.has_sprint else []

    race_results = SessionResult.objects.filter(
        race=race, session_type='race'
    ).order_by('position').select_related('driver')

    # Get weather data (cached or from FastF1)
    weather = None
    if race.is_completed:
        try:
            from core.services.fastf1_sync import FastF1SyncService
            service = FastF1SyncService(race.season)
            weather = service.get_session_weather(race, 'race')
        except Exception:
            pass

    # Check user predictions for this race
    user_prediction = None
    user_scores = []
    if request.user.is_authenticated:
        from core.models import Prediction, PredictionScore
        user_prediction = Prediction.objects.filter(
            user=request.user, race=race
        ).select_related('p1_driver', 'p2_driver', 'p3_driver')

        user_scores = PredictionScore.objects.filter(
            user=request.user, race=race
        ).order_by('session_type')

    # Active tab
    active_tab = request.GET.get('tab', 'race')

    context = {
        'race': race,
        'qualifying_results': qualifying_results,
        'sprint_results': sprint_results,
        'race_results': race_results,
        'weather': weather,
        'user_prediction': user_prediction,
        'user_scores': user_scores,
        'active_tab': active_tab,
    }
    return render(request, 'races/detail.html', context)


def race_tab_partial(request, race_id, tab):
    """HTMX partial for race detail tabs."""
    race = get_object_or_404(Race, id=race_id)

    if tab == 'qualifying':
        results = SessionResult.objects.filter(
            race=race, session_type='qualifying'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_qualifying.html', {
            'race': race, 'results': results
        })
    elif tab == 'sprint':
        results = SessionResult.objects.filter(
            race=race, session_type='sprint'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_sprint.html', {
            'race': race, 'results': results
        })
    elif tab == 'race':
        results = SessionResult.objects.filter(
            race=race, session_type='race'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_race.html', {
            'race': race, 'results': results
        })
    elif tab == 'weather':
        weather = None
        try:
            from core.services.fastf1_sync import FastF1SyncService
            service = FastF1SyncService(race.season)
            weather = service.get_session_weather(race, 'race')
        except Exception:
            pass
        return render(request, 'partials/race_tab_weather.html', {
            'race': race, 'weather': weather
        })

    return render(request, 'partials/race_tab_race.html', {'race': race, 'results': []})
