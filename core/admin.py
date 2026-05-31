"""
F1 Predictor — Django Admin Configuration

Full admin panel with inline editing, custom actions, filters, and search.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Team, Driver, DriverTeamHistory, Race, SessionResult,
    Prediction, PredictionScore, UserProfile, StandingsSnapshot
)


class DriverTeamHistoryInline(admin.TabularInline):
    model = DriverTeamHistory
    extra = 0
    fields = ('team', 'season', 'date_from', 'date_to', 'is_active')


class SessionResultInline(admin.TabularInline):
    model = SessionResult
    extra = 0
    fields = ('session_type', 'driver', 'position', 'grid_position', 'points', 'status', 'time', 'fastest_lap')
    autocomplete_fields = ['driver']


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'color_badge', 'is_active', 'driver_count')
    list_filter = ('is_active',)
    search_fields = ('name', 'short_name')
    list_editable = ('is_active',)

    def color_badge(self, obj):
        return format_html(
            '<span style="display:inline-block;width:40px;height:20px;'
            'background:{};border-radius:4px;border:1px solid #ccc;"></span> {}',
            obj.color_primary, obj.color_primary
        )
    color_badge.short_description = 'Team Color'

    def driver_count(self, obj):
        return obj.driver_history.filter(is_active=True, season=2026).count()
    driver_count.short_description = 'Active Drivers'


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'abbreviation', 'number', 'current_team_display', 'country', 'is_reserve')
    list_filter = ('is_reserve', 'team_history__team', 'country')
    search_fields = ('first_name', 'last_name', 'abbreviation')
    list_editable = ('is_reserve',)
    inlines = [DriverTeamHistoryInline]

    def current_team_display(self, obj):
        team = obj.current_team(2026)
        if team:
            return format_html(
                '<span style="color:{};">●</span> {}',
                team.color_primary, team.short_name
            )
        return '—'
    current_team_display.short_description = 'Current Team'


@admin.register(DriverTeamHistory)
class DriverTeamHistoryAdmin(admin.ModelAdmin):
    list_display = ('driver', 'team', 'season', 'date_from', 'date_to', 'is_active')
    list_filter = ('season', 'team', 'is_active')
    search_fields = ('driver__first_name', 'driver__last_name', 'team__name')
    list_editable = ('is_active', 'date_to')
    autocomplete_fields = ['driver', 'team']


@admin.register(Race)
class RaceAdmin(admin.ModelAdmin):
    list_display = ('round_display', 'name', 'country', 'race_date', 'has_sprint', 'status', 'status_badge')
    list_filter = ('season', 'has_sprint', 'status')
    search_fields = ('name', 'country', 'circuit_name')
    list_editable = ('has_sprint', 'status')
    inlines = [SessionResultInline]
    fieldsets = (
        ('Race Info', {
            'fields': ('season', 'round_number', 'name', 'official_name', 'country', 'city',
                       'circuit_name', 'fastf1_event_name')
        }),
        ('Schedule', {
            'fields': ('fp1_date', 'fp2_date', 'fp3_date', 'qualifying_date',
                       'sprint_qualifying_date', 'sprint_date', 'race_date')
        }),
        ('Status', {
            'fields': ('has_sprint', 'is_completed', 'status')
        }),
    )

    def round_display(self, obj):
        return f"R{obj.round_number:02d}"
    round_display.short_description = 'Round'

    def status_badge(self, obj):
        colors = {
            'upcoming': '#3B82F6',
            'in_progress': '#F59E0B',
            'completed': '#10B981',
            'cancelled': '#EF4444',
        }
        color = colors.get(obj.status, '#6B7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:12px;'
            'font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    actions = ['mark_completed', 'mark_upcoming', 'toggle_sprint']

    @admin.action(description='Mark selected races as completed')
    def mark_completed(self, request, queryset):
        queryset.update(status='completed', is_completed=True)

    @admin.action(description='Mark selected races as upcoming')
    def mark_upcoming(self, request, queryset):
        queryset.update(status='upcoming', is_completed=False)

    @admin.action(description='Toggle sprint weekend')
    def toggle_sprint(self, request, queryset):
        for race in queryset:
            race.has_sprint = not race.has_sprint
            race.save()


@admin.register(SessionResult)
class SessionResultAdmin(admin.ModelAdmin):
    list_display = ('race', 'session_type', 'position', 'driver', 'team_display', 'points', 'status')
    list_filter = ('session_type', 'race__season', 'race')
    search_fields = ('driver__first_name', 'driver__last_name', 'driver__abbreviation')
    autocomplete_fields = ['driver', 'race']

    def team_display(self, obj):
        team = obj.team
        if team:
            return format_html(
                '<span style="color:{};">●</span> {}',
                team.color_primary, team.short_name
            )
        return '—'
    team_display.short_description = 'Team'


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ('user', 'race', 'session_type', 'p1_driver', 'p2_driver', 'p3_driver',
                    'is_locked', 'score_display', 'created_at')
    list_filter = ('session_type', 'is_locked', 'race')
    search_fields = ('user__username',)
    autocomplete_fields = ['user', 'race', 'p1_driver', 'p2_driver', 'p3_driver']
    readonly_fields = ('created_at', 'updated_at')

    def score_display(self, obj):
        try:
            score = obj.score
            return format_html(
                '<span style="font-weight:bold;color:#10B981;">{} pts</span>',
                score.total_points
            )
        except PredictionScore.DoesNotExist:
            return '—'
    score_display.short_description = 'Score'

    actions = ['lock_predictions', 'unlock_predictions']

    @admin.action(description='Lock selected predictions')
    def lock_predictions(self, request, queryset):
        queryset.update(is_locked=True)

    @admin.action(description='Unlock selected predictions')
    def unlock_predictions(self, request, queryset):
        queryset.update(is_locked=False)


@admin.register(PredictionScore)
class PredictionScoreAdmin(admin.ModelAdmin):
    list_display = ('user', 'race', 'session_type', 'total_points',
                    'exact_p1', 'exact_p2', 'exact_p3', 'correct_drivers', 'exact_podium_bonus')
    list_filter = ('session_type', 'exact_podium_bonus', 'race')
    search_fields = ('user__username',)
    readonly_fields = ('scored_at',)

    actions = ['recalculate_scores']

    @admin.action(description='Recalculate selected scores')
    def recalculate_scores(self, request, queryset):
        from .services.scoring import PredictionScorer
        scorer = PredictionScorer()
        count = 0
        for score in queryset.select_related('prediction', 'race'):
            prediction = score.prediction
            new_score = scorer.score_prediction(prediction)
            if new_score:
                count += 1
        self.message_user(request, f"Recalculated {count} prediction scores.")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'favorite_team', 'total_points_display', 'accuracy_display')
    list_filter = ('favorite_team',)
    search_fields = ('user__username', 'user__email')

    def total_points_display(self, obj):
        return obj.total_points()
    total_points_display.short_description = 'Total Points'

    def accuracy_display(self, obj):
        return f"{obj.accuracy_percentage()}%"
    accuracy_display.short_description = 'Accuracy'


@admin.register(StandingsSnapshot)
class StandingsSnapshotAdmin(admin.ModelAdmin):
    list_display = ('season', 'round_number', 'snapshot_type', 'position', 'entity_name',
                    'points', 'wins', 'podiums')
    list_filter = ('season', 'snapshot_type', 'round_number')
    search_fields = ('driver__last_name', 'team__name')

    def entity_name(self, obj):
        if obj.snapshot_type == 'driver' and obj.driver:
            return obj.driver.full_name
        return obj.team.name
    entity_name.short_description = 'Driver/Team'
