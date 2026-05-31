"""
F1 Predictor — REST API Views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Count, Q
from django.contrib.auth.models import User

from core.models import (
    Team, Driver, Race, SessionResult, Prediction,
    PredictionScore, StandingsSnapshot
)
from core.serializers import (
    TeamSerializer, DriverSerializer, RaceSerializer, SessionResultSerializer,
    PredictionSerializer, PredictionCreateSerializer, PredictionScoreSerializer,
    StandingsSnapshotSerializer
)


class TeamViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for teams."""
    queryset = Team.objects.filter(is_active=True)
    serializer_class = TeamSerializer
    permission_classes = [AllowAny]


class DriverViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for drivers."""
    queryset = Driver.objects.all()
    serializer_class = DriverSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        team = self.request.query_params.get('team')
        if team:
            from core.models import DriverTeamHistory
            driver_ids = DriverTeamHistory.objects.filter(
                team__short_name=team, season=2026, is_active=True
            ).values_list('driver_id', flat=True)
            qs = qs.filter(id__in=driver_ids)
        return qs


class RaceViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for races."""
    queryset = Race.objects.filter(season=2026).order_by('round_number')
    serializer_class = RaceSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        race = self.get_object()
        session_type = request.query_params.get('session', 'race')
        results = SessionResult.objects.filter(
            race=race, session_type=session_type
        ).order_by('position').select_related('driver')
        serializer = SessionResultSerializer(results, many=True)
        return Response(serializer.data)


class PredictionViewSet(viewsets.ModelViewSet):
    """API endpoint for predictions."""
    serializer_class = PredictionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Prediction.objects.filter(
            user=self.request.user
        ).select_related('race', 'p1_driver', 'p2_driver', 'p3_driver')

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PredictionCreateSerializer
        return PredictionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['GET'])
def leaderboard_api(request):
    """API endpoint for prediction leaderboard."""
    season = request.query_params.get('season', 2026)
    leaderboard = PredictionScore.objects.filter(
        race__season=season
    ).values(
        'user__id', 'user__username'
    ).annotate(
        total_points=Sum('total_points'),
        predictions_count=Count('id'),
        exact_podiums=Count('id', filter=Q(exact_podium_bonus=True)),
    ).order_by('-total_points')

    return Response(list(leaderboard))


@api_view(['GET'])
def standings_api(request):
    """API endpoint for standings data (for charts)."""
    season = request.query_params.get('season', 2026)
    snapshot_type = request.query_params.get('type', 'driver')

    from core.services.standings import StandingsService
    service = StandingsService(int(season))
    data = service.get_points_progression(snapshot_type)
    return Response(data)


@api_view(['GET'])
def analytics_data_api(request):
    """API endpoint for analytics chart data."""
    season = 2026
    from core.services.standings import StandingsService
    service = StandingsService(season)

    data = {
        'driver_progression': service.get_points_progression('driver', 10),
        'constructor_progression': service.get_points_progression('constructor', 11),
    }
    return Response(data)
