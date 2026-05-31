"""
F1 Predictor — Dashboard Views
"""
import json
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.http import HttpResponse

from core.models import (
    Race, Driver, Team, SessionResult, Prediction, PredictionScore,
    UserProfile, StandingsSnapshot, DriverTeamHistory
)
from core.services.standings import StandingsService


def dashboard(request):
    """Main dashboard view. Handles HTMX partial requests via ?partial= param."""
    season = 2026

    # Score any pending predictions so the dashboard stats and mini-leaderboard are up-to-date
    from core.services.scoring import PredictionScorer
    scorer = PredictionScorer()
    scorer.score_all_pending()

    now = timezone.now()

    # Handle HTMX partial requests to avoid full page re-renders
    partial = request.GET.get('partial')
    if partial:
        return _handle_partial(request, partial, season)

    # Next upcoming race
    next_race = Race.objects.filter(
        season=season,
        race_date__gt=now,
    ).order_by('race_date').first()

    # Last completed race
    last_race = Race.objects.filter(
        season=season,
        is_completed=True,
    ).order_by('-round_number').first()

    # Recent race results (last completed race top 10)
    recent_results = []
    if last_race:
        recent_results = SessionResult.objects.filter(
            race=last_race,
            session_type='race',
        ).order_by('position').select_related('driver')[:10]

    # Driver standings (top 10)
    standings_service = StandingsService(season)
    driver_standings = standings_service.calculate_driver_standings()[:10]
    constructor_standings = standings_service.calculate_constructor_standings()[:10]

    # Prediction leaderboard
    leaderboard = PredictionScore.objects.filter(
        race__season=season,
    ).values(
        'user__id', 'user__username',
    ).annotate(
        total_points=Sum('total_points'),
        predictions_count=Count('id'),
        exact_podiums=Count('id', filter=Q(exact_podium_bonus=True)),
    ).order_by('-total_points')[:10]

    # User's recent predictions
    user_predictions = []
    if request.user.is_authenticated:
        user_predictions = Prediction.objects.filter(
            user=request.user,
            race__season=season,
        ).select_related('race', 'p1_driver', 'p2_driver', 'p3_driver').order_by(
            '-race__round_number'
        )[:5]

    # Upcoming races (next 3)
    upcoming_races = Race.objects.filter(
        season=season,
        race_date__gt=now,
    ).order_by('race_date')[:3]

    # Season progress
    total_races = Race.objects.filter(season=season).count()
    completed_races = Race.objects.filter(season=season, is_completed=True).count()
    season_progress = round((completed_races / total_races) * 100) if total_races > 0 else 0

    # User stats for performance card
    user_stats = {
        'total_points': 0,
        'global_rank': '-',
        'accuracy': 0,
    }
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            user_stats['total_points'] = profile.total_points()
            user_stats['accuracy'] = profile.accuracy_percentage()
            
            # Global rank calculation based on sum of prediction scores
            leaderboard_rank = PredictionScore.objects.values('user_id').annotate(
                total=Sum('total_points')
            ).order_by('-total')
            
            for idx, entry in enumerate(leaderboard_rank, 1):
                if entry['user_id'] == request.user.id:
                    user_stats['global_rank'] = idx
                    break
        except Exception:
            pass

    context = {
        'next_race': next_race,
        'last_race': last_race,
        'recent_results': recent_results,
        'driver_standings': driver_standings,
        'constructor_standings': constructor_standings,
        'leaderboard': leaderboard,
        'user_predictions': user_predictions,
        'upcoming_races': upcoming_races,
        'total_races': total_races,
        'completed_races': completed_races,
        'season_progress': season_progress,
        'user_stats': user_stats,
    }

    return render(request, 'dashboard/index.html', context)


def _handle_partial(request, partial, season):
    """Route HTMX partial requests to the correct template."""
    standings_service = StandingsService(season)

    if partial == 'driver_standings':
        driver_standings = standings_service.calculate_driver_standings()[:5]
        return render(request, 'partials/standings_mini.html', {
            'driver_standings': driver_standings,
            'constructor_standings': [],
        })

    elif partial == 'constructor_standings':
        constructor_standings = standings_service.calculate_constructor_standings()[:5]
        return render(request, 'partials/standings_mini.html', {
            'driver_standings': [],
            'constructor_standings': constructor_standings,
        })

    elif partial == 'recent_results':
        last_race = Race.objects.filter(
            season=season, is_completed=True,
        ).order_by('-round_number').first()
        recent_results = []
        if last_race:
            recent_results = SessionResult.objects.filter(
                race=last_race, session_type='race',
            ).order_by('position').select_related('driver')[:10]
        return render(request, 'partials/recent_results.html', {
            'last_race': last_race,
            'recent_results': recent_results,
        })

    elif partial == 'activity':
        recent_scores = PredictionScore.objects.filter(
            race__season=season,
        ).select_related('user', 'race').order_by('-scored_at')[:10]
        return render(request, 'partials/activity_feed.html', {
            'recent_scores': recent_scores,
        })

    # Unknown partial — return empty
    return HttpResponse('')


def dashboard_standings_partial(request):
    """HTMX partial for dashboard standings section."""
    season = 2026
    standings_service = StandingsService(season)
    driver_standings = standings_service.calculate_driver_standings()[:5]
    constructor_standings = standings_service.calculate_constructor_standings()[:5]

    return render(request, 'partials/standings_mini.html', {
        'driver_standings': driver_standings,
        'constructor_standings': constructor_standings,
    })


def dashboard_activity_partial(request):
    """HTMX partial for recent activity feed."""
    season = 2026
    recent_scores = PredictionScore.objects.filter(
        race__season=season,
    ).select_related('user', 'race').order_by('-scored_at')[:10]

    return render(request, 'partials/activity_feed.html', {
        'recent_scores': recent_scores,
    })


def dashboard_recent_results_partial(request):
    """HTMX partial for recent race results."""
    season = 2026
    last_race = Race.objects.filter(
        season=season, is_completed=True,
    ).order_by('-round_number').first()
    recent_results = []
    if last_race:
        recent_results = SessionResult.objects.filter(
            race=last_race, session_type='race',
        ).order_by('position').select_related('driver')[:10]
    return render(request, 'partials/recent_results.html', {
        'last_race': last_race,
        'recent_results': recent_results,
    })
