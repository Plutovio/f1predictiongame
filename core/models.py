"""
F1 Predictor — Core Models

Complete database schema for Formula 1 prediction and analytics platform.
Supports driver switches, mid-season replacements, and full historical tracking.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum, Count, Q, F


class Team(models.Model):
    """Formula 1 constructor/team."""
    name = models.CharField(max_length=100, unique=True)
    short_name = models.CharField(max_length=30)
    color_primary = models.CharField(max_length=7, default='#FFFFFF', help_text='Hex color e.g. #E8002D')
    color_secondary = models.CharField(max_length=7, default='#000000')
    logo = models.ImageField(upload_to='teams/', blank=True, null=True)
    constructor_id = models.CharField(max_length=50, blank=True, help_text='FastF1 team identifier')
    is_active = models.BooleanField(default=True)
    founded_year = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def css_class(self):
        """Return CSS class name for team color styling."""
        slug = self.short_name.lower().replace(' ', '-')
        return f'team-{slug}'

    def current_drivers(self, season=2026):
        """Get currently active drivers for this team in given season."""
        return Driver.objects.filter(
            team_history__team=self,
            team_history__season=season,
            team_history__is_active=True
        ).distinct()


class Driver(models.Model):
    """Formula 1 driver."""
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    abbreviation = models.CharField(max_length=3, unique=True)
    number = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(99)],
        null=True, blank=True
    )
    image = models.ImageField(upload_to='drivers/', blank=True, null=True)
    country = models.CharField(max_length=50, blank=True)
    country_code = models.CharField(max_length=3, blank=True, help_text='ISO 3166-1 alpha-3')
    date_of_birth = models.DateField(null=True, blank=True)
    is_reserve = models.BooleanField(default=False)
    fastf1_driver_id = models.CharField(max_length=50, blank=True, help_text='FastF1 driver identifier')
    headshot_url = models.URLField(blank=True, help_text='URL from FastF1 for driver headshot')

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.abbreviation})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def current_team(self, season=2026):
        """Get driver's current team for given season."""
        history = self.team_history.filter(
            season=season,
            is_active=True
        ).select_related('team').first()
        return history.team if history else None

    def team_at_date(self, date):
        """Get driver's team at a specific date (for historical accuracy)."""
        history = self.team_history.filter(
            date_from__lte=date,
            is_active=True
        ).filter(
            Q(date_to__gte=date) | Q(date_to__isnull=True)
        ).select_related('team').first()
        return history.team if history else None

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}" if self.first_name and self.last_name else "??"


class DriverTeamHistory(models.Model):
    """
    Tracks driver-team associations over time.
    Critical for mid-season driver swaps and reserve driver activations.

    Example: If Perez is replaced by Lawson at Red Bull after race 10,
    there would be two records:
    - Perez -> Red Bull: date_from=season_start, date_to=race_10_date, is_active=False
    - Lawson -> Red Bull: date_from=race_10_date, date_to=None, is_active=True
    """
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='team_history')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='driver_history')
    season = models.IntegerField(default=2026)
    date_from = models.DateField()
    date_to = models.DateField(null=True, blank=True, help_text='Null means currently active')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-season', '-date_from']
        verbose_name = 'Driver Team Assignment'
        verbose_name_plural = 'Driver Team Assignments'
        constraints = [
            models.UniqueConstraint(
                fields=['driver', 'team', 'season', 'date_from'],
                name='unique_driver_team_season_date'
            ),
        ]

    def __str__(self):
        status = "Active" if self.is_active else "Ended"
        return f"{self.driver.abbreviation} → {self.team.short_name} ({self.season}) [{status}]"


class Race(models.Model):
    """Formula 1 race weekend."""
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    season = models.IntegerField(default=2026)
    round_number = models.IntegerField(validators=[MinValueValidator(1)])
    name = models.CharField(max_length=200)
    official_name = models.CharField(max_length=300, blank=True)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    circuit_name = models.CharField(max_length=200, blank=True)

    # Session dates (all in UTC)
    fp1_date = models.DateTimeField(null=True, blank=True)
    fp2_date = models.DateTimeField(null=True, blank=True)
    fp3_date = models.DateTimeField(null=True, blank=True)
    qualifying_date = models.DateTimeField(null=True, blank=True)
    sprint_qualifying_date = models.DateTimeField(null=True, blank=True)
    sprint_date = models.DateTimeField(null=True, blank=True)
    race_date = models.DateTimeField()

    has_sprint = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')

    # FastF1 identifiers
    fastf1_event_name = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['season', 'round_number']
        unique_together = ['season', 'round_number']

    def __str__(self):
        return f"R{self.round_number}: {self.name} ({self.season})"

    @property
    def is_upcoming(self):
        return self.race_date > timezone.now()

    @property
    def country_emoji(self):
        """Return flag emoji for common F1 countries."""
        flags = {
            'Bahrain': '🇧🇭', 'Saudi Arabia': '🇸🇦', 'Australia': '🇦🇺',
            'Japan': '🇯🇵', 'China': '🇨🇳', 'United States': '🇺🇸',
            'USA': '🇺🇸', 'Italy': '🇮🇹', 'Monaco': '🇲🇨',
            'Canada': '🇨🇦', 'Spain': '🇪🇸', 'Austria': '🇦🇹',
            'United Kingdom': '🇬🇧', 'Great Britain': '🇬🇧',
            'Hungary': '🇭🇺', 'Belgium': '🇧🇪', 'Netherlands': '🇳🇱',
            'Singapore': '🇸🇬', 'Azerbaijan': '🇦🇿', 'Mexico': '🇲🇽',
            'Brazil': '🇧🇷', 'Qatar': '🇶🇦', 'Abu Dhabi': '🇦🇪',
            'UAE': '🇦🇪', 'Portugal': '🇵🇹', 'France': '🇫🇷',
            'Germany': '🇩🇪', 'Turkey': '🇹🇷', 'Russia': '🇷🇺',
            'Miami': '🇺🇸', 'Las Vegas': '🇺🇸',
        }
        return flags.get(self.country, '🏁')

    @property
    def next_session_date(self):
        """Get the next upcoming session date."""
        now = timezone.now()
        dates = [
            ('FP1', self.fp1_date),
            ('FP2', self.fp2_date),
            ('FP3', self.fp3_date),
            ('Qualifying', self.qualifying_date),
            ('Sprint Qualifying', self.sprint_qualifying_date),
            ('Sprint', self.sprint_date),
            ('Race', self.race_date),
        ]
        for name, dt in dates:
            if dt and dt > now:
                return name, dt
        return 'Completed', self.race_date

    def qualifying_locked(self):
        """Check if qualifying predictions should be locked."""
        if self.qualifying_date:
            return timezone.now() >= self.qualifying_date
        return False

    def sprint_locked(self):
        """Check if sprint predictions should be locked."""
        if self.sprint_date:
            return timezone.now() >= self.sprint_date
        return False

    def race_locked(self):
        """Check if race predictions should be locked."""
        return timezone.now() >= self.race_date


SESSION_TYPE_CHOICES = [
    ('qualifying', 'Qualifying'),
    ('sprint', 'Sprint'),
    ('race', 'Race'),
]


class SessionResult(models.Model):
    """
    Unified model for qualifying, sprint, and race results.
    Linked to Driver directly — team is resolved via DriverTeamHistory at race date.
    """
    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name='results')
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name='results')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    position = models.IntegerField(validators=[MinValueValidator(1)])
    grid_position = models.IntegerField(null=True, blank=True)
    points = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=50, default='Finished')
    fastest_lap = models.BooleanField(default=False)
    gap_to_leader = models.CharField(max_length=50, blank=True)
    laps_completed = models.IntegerField(default=0)
    time = models.CharField(max_length=50, blank=True, help_text='Finishing time or qualifying time')

    # Qualifying specific
    q1_time = models.CharField(max_length=20, blank=True)
    q2_time = models.CharField(max_length=20, blank=True)
    q3_time = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['position']
        unique_together = ['race', 'driver', 'session_type']
        indexes = [
            models.Index(fields=['race', 'session_type', 'position']),
            models.Index(fields=['driver', 'session_type']),
        ]

    def __str__(self):
        return f"P{self.position} {self.driver.abbreviation} - {self.race.name} ({self.session_type})"

    @property
    def team(self):
        """Get team at race date via DriverTeamHistory."""
        return self.driver.team_at_date(self.race.race_date.date())

    def _parse_time_str(self, time_str):
        if not time_str:
            return None
        val = time_str.strip()
        
        # Check for days
        days = 0
        if 'days' in val:
            parts = val.split('days')
            try:
                days = int(parts[0].strip())
            except ValueError:
                pass
            time_part = parts[1].strip()
        elif 'day' in val:
            parts = val.split('day')
            try:
                days = int(parts[0].strip())
            except ValueError:
                pass
            time_part = parts[1].strip()
        else:
            time_part = val
        
        # Check for ms
        ms = 0
        if '.' in time_part:
            time_part, ms_part = time_part.split('.')
            try:
                ms = int(ms_part[:3])
            except ValueError:
                pass
        
        time_subparts = time_part.split(':')
        hours = 0
        minutes = 0
        seconds = 0
        try:
            if len(time_subparts) == 3:
                hours = int(time_subparts[0])
                minutes = int(time_subparts[1])
                seconds = int(time_subparts[2])
            elif len(time_subparts) == 2:
                minutes = int(time_subparts[0])
                seconds = int(time_subparts[1])
            elif len(time_subparts) == 1:
                seconds = int(time_subparts[0])
        except ValueError:
            pass
        
        return days, hours, minutes, seconds, ms

    def _format_absolute_time_from_str(self, time_str):
        if not time_str:
            return ""
        parsed = self._parse_time_str(time_str)
        if not parsed:
            return time_str
        days, hours, minutes, seconds, ms = parsed
        total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
        
        abs_hours = total_seconds // 3600
        abs_mins = (total_seconds % 3600) // 60
        abs_secs = total_seconds % 60
        
        if abs_hours > 0:
            return f"{abs_hours}:{abs_mins:02d}:{abs_secs:02d}.{ms:03d}"
        elif abs_mins > 0:
            return f"{abs_mins}:{abs_secs:02d}.{ms:03d}"
        else:
            return f"{abs_secs}.{ms:03d}"

    @property
    def formatted_time(self):
        if not self.time:
            return ""
        
        # If it's a DNF status, return it directly
        if self.is_dnf:
            return self.status
            
        parsed = self._parse_time_str(self.time)
        if not parsed:
            return self.time
            
        days, hours, minutes, seconds, ms = parsed
        total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
        
        is_gap = (self.session_type in ('race', 'sprint') and self.position > 1)
        
        if is_gap:
            if total_seconds < 60:
                return f"+{total_seconds}.{ms:03d}"
            else:
                gap_minutes = total_seconds // 60
                gap_secs = total_seconds % 60
                return f"+{gap_minutes}:{gap_secs:02d}.{ms:03d}"
        else:
            # Absolute time format
            abs_hours = total_seconds // 3600
            abs_mins = (total_seconds % 3600) // 60
            abs_secs = total_seconds % 60
            
            if abs_hours > 0:
                return f"{abs_hours}:{abs_mins:02d}:{abs_secs:02d}.{ms:03d}"
            elif abs_mins > 0:
                return f"{abs_mins}:{abs_secs:02d}.{ms:03d}"
            else:
                return f"{abs_secs}.{ms:03d}"

    @property
    def formatted_q1(self):
        return self._format_absolute_time_from_str(self.q1_time)

    @property
    def formatted_q2(self):
        return self._format_absolute_time_from_str(self.q2_time)

    @property
    def formatted_q3(self):
        return self._format_absolute_time_from_str(self.q3_time)

    @property
    def is_podium(self):
        return self.position <= 3

    @property
    def is_dnf(self):
        return self.status not in ('Finished', '+1 Lap', '+2 Laps', '+3 Laps')


class Prediction(models.Model):
    """
    User prediction for a race session's top 3 podium/qualifying positions.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predictions')
    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name='predictions')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)
    p1_driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name='predicted_p1',
        verbose_name='Predicted P1'
    )
    p2_driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name='predicted_p2',
        verbose_name='Predicted P2'
    )
    p3_driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name='predicted_p3',
        verbose_name='Predicted P3'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ['user', 'race', 'session_type']
        ordering = ['-race__round_number']
        indexes = [
            models.Index(fields=['user', 'race']),
            models.Index(fields=['race', 'session_type']),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.race.name} {self.session_type}"

    @property
    def predicted_podium(self):
        """Return predicted drivers as ordered list."""
        return [self.p1_driver, self.p2_driver, self.p3_driver]

    def should_be_locked(self):
        """Check if this prediction should be locked based on session time."""
        if self.session_type == 'qualifying':
            return self.race.qualifying_locked()
        elif self.session_type == 'sprint':
            return self.race.sprint_locked()
        else:
            return self.race.race_locked()

    def lock_if_needed(self):
        """Auto-lock if session has started."""
        if not self.is_locked and self.should_be_locked():
            self.is_locked = True
            self.save(update_fields=['is_locked'])
            return True
        return False


class PredictionScore(models.Model):
    """
    Scored prediction with point breakdown.

    Scoring:
      - Exact P1: 5 points
      - Exact P2: 4 points
      - Exact P3: 3 points
      - Correct driver, wrong position: 1 point each
      - Exact podium bonus (all 3 exact): 3 bonus points
      - Maximum per session: 15 points
    """
    prediction = models.OneToOneField(Prediction, on_delete=models.CASCADE, related_name='score')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prediction_scores')
    race = models.ForeignKey(Race, on_delete=models.CASCADE, related_name='prediction_scores')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES)

    exact_p1 = models.BooleanField(default=False)
    exact_p2 = models.BooleanField(default=False)
    exact_p3 = models.BooleanField(default=False)
    correct_drivers = models.IntegerField(default=0, help_text='Drivers in top 3 but wrong position')
    exact_podium_bonus = models.BooleanField(default=False, help_text='All 3 positions exact')
    total_points = models.IntegerField(default=0)

    # Actual results stored for quick reference
    actual_p1 = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    actual_p2 = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    actual_p3 = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    scored_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-total_points']
        indexes = [
            models.Index(fields=['user', 'total_points']),
            models.Index(fields=['race', 'session_type']),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.race.name} {self.session_type}: {self.total_points}pts"


class UserProfile(models.Model):
    """Extended user profile for F1 Predictor."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    favorite_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)

    class Meta:
        verbose_name = 'User Profile'

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def initials(self):
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name[0]}{self.user.last_name[0]}".upper()
        return self.user.username[:2].upper()

    @property
    def team_color(self):
        if self.favorite_team:
            return self.favorite_team.color_primary
        return '#E10600'  # Default F1 red

    def total_points(self):
        return self.user.prediction_scores.aggregate(
            total=Sum('total_points')
        )['total'] or 0

    def total_predictions(self):
        return self.user.predictions.count()

    def accuracy_percentage(self):
        scores = self.user.prediction_scores.all()
        if not scores.exists():
            return 0
        total_possible = scores.count() * 15  # Max 15 per session
        actual = scores.aggregate(total=Sum('total_points'))['total'] or 0
        return round((actual / total_possible) * 100, 1) if total_possible > 0 else 0

    def exact_predictions(self):
        return self.user.prediction_scores.filter(exact_podium_bonus=True).count()

    def current_streak(self):
        """Calculate current scoring streak (consecutive races with points > 0)."""
        scores = self.user.prediction_scores.order_by('-race__round_number')
        streak = 0
        for score in scores:
            if score.total_points > 0:
                streak += 1
            else:
                break
        return streak


class StandingsSnapshot(models.Model):
    """
    Snapshot of championship standings after each round.
    Used for points progression charts.
    """
    SNAPSHOT_TYPE_CHOICES = [
        ('driver', 'Driver'),
        ('constructor', 'Constructor'),
    ]

    season = models.IntegerField(default=2026)
    round_number = models.IntegerField()
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, null=True, blank=True, related_name='standings')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='standings')
    points = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    position = models.IntegerField()
    snapshot_type = models.CharField(max_length=15, choices=SNAPSHOT_TYPE_CHOICES)
    wins = models.IntegerField(default=0)
    podiums = models.IntegerField(default=0)

    class Meta:
        ordering = ['season', 'round_number', 'position']
        indexes = [
            models.Index(fields=['season', 'round_number', 'snapshot_type']),
            models.Index(fields=['driver', 'season']),
            models.Index(fields=['team', 'season']),
        ]

    def __str__(self):
        entity = self.driver.abbreviation if self.driver else self.team.short_name
        return f"R{self.round_number} P{self.position}: {entity} ({self.points}pts)"


# ============================================================
# Signals for auto-creating UserProfile
# ============================================================
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
