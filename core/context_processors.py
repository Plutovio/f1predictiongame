"""
F1 Predictor — Context Processors

Provides global template context data.
"""
from django.utils import timezone
from core.models import Race, Team


def f1_context(request):
    """Add F1-specific context to all templates."""
    season = 2026
    now = timezone.now()

    # Next upcoming race
    next_race = Race.objects.filter(
        season=season,
        race_date__gt=now,
    ).order_by('race_date').first()

    # All teams for nav/filters
    teams = Team.objects.filter(is_active=True).order_by('name')

    context = {
        'current_season': season,
        'next_race_global': next_race,
        'all_teams': teams,
        'current_year': now.year,
    }

    # User profile if authenticated
    if request.user.is_authenticated:
        try:
            context['user_profile'] = request.user.profile
        except Exception:
            pass

    return context
