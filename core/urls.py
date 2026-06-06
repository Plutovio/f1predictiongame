"""
F1 Predictor — Core URL Configuration
"""
from django.urls import path
from core.views.dashboard import dashboard, dashboard_standings_partial, dashboard_activity_partial, dashboard_recent_results_partial
from core.views.standings import driver_standings, constructor_standings, driver_detail, team_detail
from core.views.races import race_calendar, race_detail, race_tab_partial, sync_race_results_view
from core.views.predictions import make_prediction, prediction_results, prediction_leaderboard, user_predictions_list
from core.views.analytics import analytics

urlpatterns = [
    # Dashboard
    path('', dashboard, name='dashboard'),
    path('partials/standings/', dashboard_standings_partial, name='partial_standings'),
    path('partials/standings-mini/', dashboard_standings_partial, name='partial_standings_mini'),
    path('partials/activity/', dashboard_activity_partial, name='partial_activity'),
    path('partials/recent-results/', dashboard_recent_results_partial, name='partial_recent_results'),
    path('predictions/', user_predictions_list, name='user_predictions_list'),

    # Standings
    path('standings/drivers/', driver_standings, name='driver_standings'),
    path('standings/constructors/', constructor_standings, name='constructor_standings'),
    path('drivers/<int:driver_id>/', driver_detail, name='driver_detail'),
    path('teams/<int:team_id>/', team_detail, name='team_detail'),

    # Races
    path('races/', race_calendar, name='race_calendar'),
    path('races/<int:race_id>/', race_detail, name='race_detail'),
    path('races/<int:race_id>/tab/<str:tab>/', race_tab_partial, name='race_tab'),
    path('races/<int:race_id>/sync/', sync_race_results_view, name='sync_race_results'),

    # Predictions
    path('predict/<int:race_id>/', make_prediction, name='make_prediction'),
    path('predictions/<int:race_id>/results/', prediction_results, name='prediction_results'),
    path('leaderboard/', prediction_leaderboard, name='prediction_leaderboard'),

    # Analytics
    path('analytics/', analytics, name='analytics'),
]
