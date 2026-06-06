"""
F1 Predictor — Race Views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from core.services.fastf1_sync import FastF1SyncService
from core.services.scoring import PredictionScorer
from core.services.standings import StandingsService
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
    fp1_results = SessionResult.objects.filter(
        race=race, session_type='fp1'
    ).order_by('position').select_related('driver')

    fp2_results = SessionResult.objects.filter(
        race=race, session_type='fp2'
    ).order_by('position').select_related('driver')

    fp3_results = SessionResult.objects.filter(
        race=race, session_type='fp3'
    ).order_by('position').select_related('driver')

    sprint_qualifying_results = SessionResult.objects.filter(
        race=race, session_type='sprint_qualifying'
    ).order_by('position').select_related('driver') if race.has_sprint else []

    qualifying_results = SessionResult.objects.filter(
        race=race, session_type='qualifying'
    ).order_by('position').select_related('driver')

    sprint_results = SessionResult.objects.filter(
        race=race, session_type='sprint'
    ).order_by('position').select_related('driver') if race.has_sprint else []

    race_results = SessionResult.objects.filter(
        race=race, session_type='race'
    ).order_by('position').select_related('driver')



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
        'fp1_results': fp1_results,
        'fp2_results': fp2_results,
        'fp3_results': fp3_results,
        'sprint_qualifying_results': sprint_qualifying_results,
        'qualifying_results': qualifying_results,
        'sprint_results': sprint_results,
        'race_results': race_results,
        'user_prediction': user_prediction,
        'user_scores': user_scores,
        'active_tab': active_tab,
    }
    return render(request, 'races/detail.html', context)


def race_tab_partial(request, race_id, tab):
    """HTMX partial for race detail tabs."""
    race = get_object_or_404(Race, id=race_id)

    if tab == 'fp1':
        results = SessionResult.objects.filter(
            race=race, session_type='fp1'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_practice.html', {
            'race': race, 'results': results, 'session_name': 'Free Practice 1', 'session_type': 'fp1'
        })
    elif tab == 'fp2':
        results = SessionResult.objects.filter(
            race=race, session_type='fp2'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_practice.html', {
            'race': race, 'results': results, 'session_name': 'Free Practice 2', 'session_type': 'fp2'
        })
    elif tab == 'fp3':
        results = SessionResult.objects.filter(
            race=race, session_type='fp3'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_practice.html', {
            'race': race, 'results': results, 'session_name': 'Free Practice 3', 'session_type': 'fp3'
        })
    elif tab == 'sprint_qualifying':
        results = SessionResult.objects.filter(
            race=race, session_type='sprint_qualifying'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_qualifying.html', {
            'race': race, 'results': results, 'session_name': 'Sprint Shootout', 'session_type': 'sprint_qualifying'
        })
    elif tab == 'qualifying':
        results = SessionResult.objects.filter(
            race=race, session_type='qualifying'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_qualifying.html', {
            'race': race, 'results': results, 'session_name': 'Qualifying', 'session_type': 'qualifying'
        })
    elif tab == 'sprint':
        results = SessionResult.objects.filter(
            race=race, session_type='sprint'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_sprint.html', {
            'race': race, 'results': results, 'session_name': 'Sprint', 'session_type': 'sprint'
        })
    elif tab == 'race':
        results = SessionResult.objects.filter(
            race=race, session_type='race'
        ).order_by('position').select_related('driver')
        return render(request, 'partials/race_tab_race.html', {
            'race': race, 'results': results, 'session_name': 'Race', 'session_type': 'race'
        })

    return render(request, 'partials/race_tab_race.html', {'race': race, 'results': []})


@staff_member_required
@require_POST
def sync_race_results_view(request, race_id):
    """Staff-only view to sync race results on demand."""
    race = get_object_or_404(Race, id=race_id)
    session_type = request.GET.get('session')
    try:
        service = FastF1SyncService(race.season)
        if session_type:
            count = service.sync_session_results(race, session_type, force=True)
            
            # Score predictions if applicable
            if session_type in ['qualifying', 'sprint', 'race']:
                scorer = PredictionScorer()
                scorer.score_race_predictions(race, session_type)
                
                if session_type == 'race':
                    race.status = 'completed'
                    race.is_completed = True
                    race.save(update_fields=['status', 'is_completed'])
                
                # Create standings snapshot
                standings = StandingsService(race.season)
                standings.create_standings_snapshot(race.round_number)
                
            messages.success(request, f"Successfully synced {session_type.upper()} results ({count} records) for {race.name}.")
        else:
            count = service.sync_race_all_sessions(race, force=True)
            
            # Mark race as completed if race results were successfully fetched
            has_race_results = SessionResult.objects.filter(race=race, session_type='race').exists()
            if has_race_results:
                race.status = 'completed'
                race.is_completed = True
                race.save(update_fields=['status', 'is_completed'])
            
            # Score predictions for this race
            scorer = PredictionScorer()
            for st in ['qualifying', 'sprint', 'race']:
                scorer.score_race_predictions(race, st)
            
            # Create standings snapshot
            standings = StandingsService(race.season)
            standings.create_standings_snapshot(race.round_number)
            
            messages.success(request, f"Successfully synced all session results ({count} records) for {race.name}.")
    except Exception as e:
        messages.error(request, f"Failed to sync results: {e}")
        
    return redirect(f"/races/{race.id}/?tab={session_type or 'schedule'}")
