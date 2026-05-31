"""
F1 Predictor — Prediction Views
"""
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Sum, Count, Q, Avg

from core.models import (
    Race, Driver, Prediction, PredictionScore, DriverTeamHistory
)
from core.services.scoring import PredictionScorer, get_head_to_head


@login_required
def make_prediction(request, race_id):
    """Create or edit predictions for a race."""
    race = get_object_or_404(Race, id=race_id)
    season = race.season

    # Get active drivers for this season
    active_driver_ids = DriverTeamHistory.objects.filter(
        season=season, is_active=True
    ).values_list('driver_id', flat=True)

    drivers = Driver.objects.filter(
        id__in=active_driver_ids, is_reserve=False
    ).select_related().order_by('last_name')

    # Attach team info to each driver
    driver_list = []
    for driver in drivers:
        team = driver.current_team(season)
        driver_list.append({
            'driver': driver,
            'team': team,
            'color': team.color_primary if team else '#FFFFFF',
            'team_name': team.short_name if team else 'Unknown',
        })

    # Get existing predictions
    existing_predictions = {}
    for session_type in ['qualifying', 'sprint', 'race']:
        pred = Prediction.objects.filter(
            user=request.user, race=race, session_type=session_type
        ).select_related('p1_driver', 'p2_driver', 'p3_driver').first()
        if pred:
            existing_predictions[session_type] = pred

    # Check lock status
    is_quali_locked = race.qualifying_locked()
    is_sprint_locked = race.sprint_locked()
    is_race_locked = race.race_locked()

    if request.method == 'POST':
        session_type = request.POST.get('session_type')
        p1_id = request.POST.get('p1_driver')
        p2_id = request.POST.get('p2_driver')
        p3_id = request.POST.get('p3_driver')

        # Validate
        if not all([session_type, p1_id, p2_id, p3_id]):
            messages.error(request, 'Please select drivers for all three positions.')
            return redirect('make_prediction', race_id=race.id)

        # Check if locked
        if session_type == 'qualifying' and is_quali_locked:
            messages.error(request, 'Qualifying predictions are locked.')
            return redirect('make_prediction', race_id=race.id)
        if session_type == 'sprint' and is_sprint_locked:
            messages.error(request, 'Sprint predictions are locked.')
            return redirect('make_prediction', race_id=race.id)
        if session_type == 'race' and is_race_locked:
            messages.error(request, 'Race predictions are locked.')
            return redirect('make_prediction', race_id=race.id)

        # Validate unique drivers
        if len(set([p1_id, p2_id, p3_id])) < 3:
            messages.error(request, 'Please select three different drivers.')
            return redirect('make_prediction', race_id=race.id)

        try:
            p1 = Driver.objects.get(id=p1_id)
            p2 = Driver.objects.get(id=p2_id)
            p3 = Driver.objects.get(id=p3_id)

            prediction, created = Prediction.objects.update_or_create(
                user=request.user,
                race=race,
                session_type=session_type,
                defaults={
                    'p1_driver': p1,
                    'p2_driver': p2,
                    'p3_driver': p3,
                }
            )

            action = 'submitted' if created else 'updated'
            messages.success(
                request,
                f'Your {session_type} prediction for {race.name} has been {action}!'
            )

            # If HTMX request, return partial
            if request.headers.get('HX-Request'):
                return render(request, 'predictions/_prediction_saved.html', {
                    'prediction': prediction,
                    'session_type': session_type,
                })

            return redirect('make_prediction', race_id=race.id)

        except Driver.DoesNotExist:
            messages.error(request, 'Invalid driver selection.')
            return redirect('make_prediction', race_id=race.id)

    context = {
        'race': race,
        'drivers': driver_list,
        'existing_predictions': existing_predictions,
        'is_quali_locked': is_quali_locked,
        'is_sprint_locked': is_sprint_locked,
        'is_race_locked': is_race_locked,
    }
    return render(request, 'predictions/make.html', context)


@login_required
def prediction_results(request, race_id):
    """View prediction results and scoring for a race."""
    race = get_object_or_404(Race, id=race_id)

    # Score pending predictions for this race before displaying results
    from core.services.scoring import PredictionScorer
    scorer = PredictionScorer()
    scorer.score_race_predictions(race)

    # Get all predictions for this race
    all_predictions = Prediction.objects.filter(
        race=race
    ).select_related('user', 'p1_driver', 'p2_driver', 'p3_driver')

    # Get actual results
    from core.models import SessionResult
    actual_results = {}
    for session_type in ['qualifying', 'sprint', 'race']:
        results = SessionResult.objects.filter(
            race=race, session_type=session_type, position__lte=3
        ).order_by('position').select_related('driver')
        if results.exists():
            actual_results[session_type] = list(results)

    # Get user's predictions and scores
    user_predictions = all_predictions.filter(user=request.user)
    user_scores = PredictionScore.objects.filter(
        user=request.user, race=race
    ).select_related('prediction', 'actual_p1', 'actual_p2', 'actual_p3')

    # Get other users' scores for comparison
    other_scores = PredictionScore.objects.filter(
        race=race
    ).exclude(user=request.user).select_related('user')

    # Total points per user for this race
    race_totals = PredictionScore.objects.filter(
        race=race
    ).values('user__username').annotate(
        total=Sum('total_points')
    ).order_by('-total')

    context = {
        'race': race,
        'user_predictions': user_predictions,
        'user_scores': user_scores,
        'actual_results': actual_results,
        'race_totals': race_totals,
        'other_scores': other_scores,
    }
    return render(request, 'predictions/results.html', context)


def prediction_leaderboard(request):
    """Overall prediction leaderboard."""
    season = 2026

    # Score any pending predictions before showing leaderboard
    from core.services.scoring import PredictionScorer
    scorer = PredictionScorer()
    scorer.score_all_pending()

    # Overall leaderboard
    leaderboard = PredictionScore.objects.filter(
        race__season=season,
    ).values(
        'user__id', 'user__username',
    ).annotate(
        total_pts=Sum('total_points'),
        predictions_count=Count('id'),
        exact_podiums=Count('id', filter=Q(exact_podium_bonus=True)),
        exact_p1s=Count('id', filter=Q(exact_p1=True)),
    ).order_by('-total_pts')

    # Calculate avg manually for each entry
    for entry in leaderboard:
        if entry['predictions_count'] > 0:
            entry['avg_points'] = round(entry['total_pts'] / entry['predictions_count'], 1)
        else:
            entry['avg_points'] = 0

    # Race-by-race breakdown
    from django.contrib.auth.models import User
    users = User.objects.filter(
        prediction_scores__race__season=season
    ).distinct()

    races = Race.objects.filter(
        season=season, is_completed=True
    ).order_by('round_number')

    race_breakdown = []
    for race in races:
        race_data = {'race': race, 'scores': {}}
        for user in users:
            total = PredictionScore.objects.filter(
                user=user, race=race
            ).aggregate(total=Sum('total_points'))['total'] or 0
            race_data['scores'][user.username] = total
        race_breakdown.append(race_data)

    # Head-to-head (if two users)
    h2h = None
    user_list = list(users)
    if len(user_list) >= 2:
        h2h = get_head_to_head(user_list[0], user_list[1], season)

    context = {
        'leaderboard': leaderboard,
        'race_breakdown': race_breakdown,
        'races': races,
        'users': users,
        'h2h': h2h,
        'h2h_json': json.dumps(h2h) if h2h else '{}',
    }
    return render(request, 'predictions/leaderboard.html', context)


@login_required
def user_predictions_list(request):
    """List of all races in the season with the user's predictions for each."""
    season = 2026
    races = Race.objects.filter(season=season).order_by('round_number')
    
    # Pre-fetch predictions and scores for the current user
    predictions = Prediction.objects.filter(
        user=request.user, race__season=season
    ).select_related('p1_driver', 'p2_driver', 'p3_driver')
    
    scores = PredictionScore.objects.filter(
        user=request.user, race__season=season
    )
    
    # Map predictions and scores by race_id and session_type for easy template lookup
    pred_map = {}
    for p in predictions:
        if p.race_id not in pred_map:
            pred_map[p.race_id] = {}
        pred_map[p.race_id][p.session_type] = p
        
    score_map = {}
    for s in scores:
        if s.race_id not in score_map:
            score_map[s.race_id] = {}
        score_map[s.race_id][s.session_type] = s
        
    # Build race list with annotated prediction data
    race_list = []
    for race in races:
        race_preds = pred_map.get(race.id, {})
        race_scores = score_map.get(race.id, {})
        
        # Calculate total score for this race
        total_score = sum(s.total_points for s in race_scores.values())
        
        race_list.append({
            'race': race,
            'predictions': race_preds,
            'scores': race_scores,
            'total_score': total_score,
            'has_any_prediction': len(race_preds) > 0,
        })
        
    context = {
        'races': race_list,
    }
    return render(request, 'predictions/user_list.html', context)
