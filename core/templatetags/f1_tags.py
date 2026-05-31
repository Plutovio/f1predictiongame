"""
F1 Predictor — Custom Template Tags and Filters
"""
from django import template
from django.utils import timezone
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def team_color(driver, season=2026):
    """Get team color for a driver."""
    team = driver.current_team(season) if hasattr(driver, 'current_team') else None
    return team.color_primary if team else '#FFFFFF'


@register.filter
def team_name(driver, season=2026):
    """Get team name for a driver."""
    team = driver.current_team(season) if hasattr(driver, 'current_team') else None
    return team.short_name if team else 'Unknown'


@register.filter
def position_class(position):
    """Return CSS class for position styling."""
    if position == 1:
        return 'text-yellow-400'
    elif position == 2:
        return 'text-gray-300'
    elif position == 3:
        return 'text-amber-600'
    return 'text-white'


@register.filter
def position_badge(position):
    """Return styled position badge HTML."""
    colors = {
        1: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
        2: 'bg-gray-400/20 text-gray-300 border-gray-400/30',
        3: 'bg-amber-700/20 text-amber-500 border-amber-700/30',
    }
    style = colors.get(position, 'bg-white/5 text-gray-400 border-white/10')
    return mark_safe(
        f'<span class="inline-flex items-center justify-center w-8 h-8 rounded-lg border text-sm font-bold {style}">'
        f'P{position}</span>'
    )


@register.filter
def score_color(points):
    """Return color based on score points."""
    if points >= 12:
        return 'text-green-400'
    elif points >= 8:
        return 'text-emerald-400'
    elif points >= 4:
        return 'text-yellow-400'
    elif points > 0:
        return 'text-orange-400'
    return 'text-red-400'


@register.filter
def initials(user):
    """Get user initials."""
    if hasattr(user, 'first_name') and user.first_name and user.last_name:
        return f"{user.first_name[0]}{user.last_name[0]}".upper()
    if hasattr(user, 'username'):
        return user.username[:2].upper()
    return '??'


@register.filter
def time_until(dt):
    """Get human-readable time until a datetime."""
    if not dt:
        return 'TBD'
    now = timezone.now()
    if dt < now:
        return 'Completed'
    diff = dt - now
    days = diff.days
    hours = diff.seconds // 3600
    if days > 0:
        return f'{days}d {hours}h'
    elif hours > 0:
        minutes = (diff.seconds % 3600) // 60
        return f'{hours}h {minutes}m'
    else:
        minutes = diff.seconds // 60
        return f'{minutes}m'


@register.filter
def multiply(value, arg):
    """Multiply two values."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Calculate percentage."""
    try:
        if total == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.simple_tag
def team_color_style(team):
    """Generate inline style for team color."""
    if team:
        return mark_safe(f'style="border-left: 3px solid {team.color_primary};"')
    return ''


@register.inclusion_tag('components/driver_card.html')
def driver_card(driver, team=None, size='md', show_number=True):
    """Render a driver card component."""
    if not team and hasattr(driver, 'current_team'):
        team = driver.current_team(2026)
    return {
        'driver': driver,
        'team': team,
        'size': size,
        'show_number': show_number,
    }


@register.filter
def split_to_list(val):
    """
    Split a comma-separated string, then split each segment by spaces.
    e.g. "1 P1 #FFD700,2 P2 #C0C0C0" -> [['1', 'P1', '#FFD700'], ['2', 'P2', '#C0C0C0']]
    """
    if not val:
        return []
    parts = val.split(',')
    result = []
    for part in parts:
        result.append(part.strip().split())
    return result
