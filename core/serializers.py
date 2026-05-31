"""
F1 Predictor — REST API Serializers
"""
from rest_framework import serializers
from core.models import (
    Team, Driver, Race, SessionResult, Prediction,
    PredictionScore, StandingsSnapshot, UserProfile
)


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'short_name', 'color_primary', 'color_secondary', 'is_active']


class DriverSerializer(serializers.ModelSerializer):
    team = serializers.SerializerMethodField()

    class Meta:
        model = Driver
        fields = ['id', 'first_name', 'last_name', 'abbreviation', 'number',
                  'country', 'is_reserve', 'headshot_url', 'team']

    def get_team(self, obj):
        team = obj.current_team(2026)
        if team:
            return TeamSerializer(team).data
        return None


class RaceSerializer(serializers.ModelSerializer):
    country_emoji = serializers.ReadOnlyField()

    class Meta:
        model = Race
        fields = ['id', 'season', 'round_number', 'name', 'country', 'city',
                  'circuit_name', 'race_date', 'qualifying_date', 'sprint_date',
                  'has_sprint', 'is_completed', 'status', 'country_emoji']


class SessionResultSerializer(serializers.ModelSerializer):
    driver = DriverSerializer(read_only=True)

    class Meta:
        model = SessionResult
        fields = ['id', 'driver', 'session_type', 'position', 'grid_position',
                  'points', 'status', 'fastest_lap', 'gap_to_leader', 'time',
                  'q1_time', 'q2_time', 'q3_time']


class PredictionSerializer(serializers.ModelSerializer):
    p1_driver = DriverSerializer(read_only=True)
    p2_driver = DriverSerializer(read_only=True)
    p3_driver = DriverSerializer(read_only=True)

    class Meta:
        model = Prediction
        fields = ['id', 'race', 'session_type', 'p1_driver', 'p2_driver',
                  'p3_driver', 'is_locked', 'created_at']
        read_only_fields = ['is_locked', 'created_at']


class PredictionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = ['race', 'session_type', 'p1_driver', 'p2_driver', 'p3_driver']

    def validate(self, data):
        drivers = [data['p1_driver'], data['p2_driver'], data['p3_driver']]
        if len(set(d.id for d in drivers)) < 3:
            raise serializers.ValidationError("All three drivers must be different.")
        return data


class PredictionScoreSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    race = RaceSerializer(read_only=True)

    class Meta:
        model = PredictionScore
        fields = ['id', 'user', 'race', 'session_type', 'exact_p1', 'exact_p2',
                  'exact_p3', 'correct_drivers', 'exact_podium_bonus', 'total_points']


class StandingsSnapshotSerializer(serializers.ModelSerializer):
    driver = DriverSerializer(read_only=True)
    team = TeamSerializer(read_only=True)

    class Meta:
        model = StandingsSnapshot
        fields = ['season', 'round_number', 'driver', 'team', 'points',
                  'position', 'snapshot_type', 'wins', 'podiums']
