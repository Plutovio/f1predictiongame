"""
F1 Predictor — API URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.api.views import (
    TeamViewSet, DriverViewSet, RaceViewSet, PredictionViewSet,
    leaderboard_api, standings_api, analytics_data_api
)

router = DefaultRouter()
router.register(r'teams', TeamViewSet)
router.register(r'drivers', DriverViewSet)
router.register(r'races', RaceViewSet)
router.register(r'predictions', PredictionViewSet, basename='prediction')

urlpatterns = [
    path('', include(router.urls)),
    path('leaderboard/', leaderboard_api, name='api_leaderboard'),
    path('standings/', standings_api, name='api_standings'),
    path('analytics/', analytics_data_api, name='api_analytics'),
]
