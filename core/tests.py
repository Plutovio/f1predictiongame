import datetime
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import (
    Team, Driver, DriverTeamHistory, Race, SessionResult, Prediction, PredictionScore, StandingsSnapshot
)
from core.services.standings import StandingsService
from core.services.scoring import PredictionScorer, get_head_to_head, get_leaderboard

class F1PredictorTestCase(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.user2 = User.objects.create_user(username='testuser2', password='password123')

        # Create teams
        self.ferrari = Team.objects.create(
            name='Ferrari',
            short_name='Ferrari',
            color_primary='#E8002D',
            constructor_id='ferrari',
            is_active=True
        )
        self.mclaren = Team.objects.create(
            name='McLaren',
            short_name='McLaren',
            color_primary='#FF8000',
            constructor_id='mclaren',
            is_active=True
        )

        # Create drivers
        self.leclerc = Driver.objects.create(
            first_name='Charles',
            last_name='Leclerc',
            abbreviation='LEC',
            number=16,
            is_reserve=False,
            fastf1_driver_id='leclerc'
        )
        self.norris = Driver.objects.create(
            first_name='Lando',
            last_name='Norris',
            abbreviation='NOR',
            number=4,
            is_reserve=False,
            fastf1_driver_id='norris'
        )
        self.hamilton = Driver.objects.create(
            first_name='Lewis',
            last_name='Hamilton',
            abbreviation='HAM',
            number=44,
            is_reserve=False,
            fastf1_driver_id='hamilton'
        )

        # Create history (active in 2026)
        self.history_lec = DriverTeamHistory.objects.create(
            driver=self.leclerc,
            team=self.ferrari,
            season=2026,
            date_from=datetime.date(2026, 1, 1),
            is_active=True
        )
        self.history_nor = DriverTeamHistory.objects.create(
            driver=self.norris,
            team=self.mclaren,
            season=2026,
            date_from=datetime.date(2026, 1, 1),
            is_active=True
        )
        self.history_ham = DriverTeamHistory.objects.create(
            driver=self.hamilton,
            team=self.ferrari,
            season=2026,
            date_from=datetime.date(2026, 1, 1),
            is_active=True
        )

        # Create races (2026)
        self.race1 = Race.objects.create(
            season=2026,
            round_number=1,
            name='Australian Grand Prix',
            country='Australia',
            qualifying_date=timezone.now() - datetime.timedelta(days=2),
            race_date=timezone.now() - datetime.timedelta(days=1),
            is_completed=True,
            status='completed'
        )
        self.race2 = Race.objects.create(
            season=2026,
            round_number=2,
            name='Chinese Grand Prix',
            country='China',
            qualifying_date=timezone.now() + datetime.timedelta(days=1),
            race_date=timezone.now() + datetime.timedelta(days=2),
            is_completed=False,
            status='upcoming'
        )

    def test_driver_team_association(self):
        """Test current_team property of drivers."""
        self.assertEqual(self.leclerc.current_team(2026), self.ferrari)
        self.assertEqual(self.norris.current_team(2026), self.mclaren)
        self.assertEqual(self.leclerc.team_at_date(datetime.date(2026, 2, 15)), self.ferrari)

    def test_standings_calculation(self):
        """Test standings service calculations."""
        # Create results for Race 1
        # P1: Norris (25pts), P2: Leclerc (18pts), P3: Hamilton (15pts)
        SessionResult.objects.create(race=self.race1, driver=self.norris, session_type='race', position=1, points=Decimal('25'))
        SessionResult.objects.create(race=self.race1, driver=self.leclerc, session_type='race', position=2, points=Decimal('18'))
        SessionResult.objects.create(race=self.race1, driver=self.hamilton, session_type='race', position=3, points=Decimal('15'))

        # Calculate driver standings
        standings_service = StandingsService(season=2026)
        driver_standings = standings_service.calculate_driver_standings()

        # Should be Norris -> Leclerc -> Hamilton
        self.assertEqual(len(driver_standings), 3)
        self.assertEqual(driver_standings[0]['driver'], self.norris)
        self.assertEqual(driver_standings[0]['points'], Decimal('25'))
        self.assertEqual(driver_standings[0]['position'], 1)
        self.assertEqual(driver_standings[0]['wins'], 1)

        self.assertEqual(driver_standings[1]['driver'], self.leclerc)
        self.assertEqual(driver_standings[1]['points'], Decimal('18'))
        self.assertEqual(driver_standings[1]['position'], 2)

        # Calculate constructor standings
        # Ferrari: Leclerc (18) + Hamilton (15) = 33
        # McLaren: Norris (25) = 25
        constructor_standings = standings_service.calculate_constructor_standings()
        self.assertEqual(len(constructor_standings), 2)
        self.assertEqual(constructor_standings[0]['team'], self.ferrari)
        self.assertEqual(constructor_standings[0]['points'], Decimal('33'))
        self.assertEqual(constructor_standings[0]['position'], 1)

        self.assertEqual(constructor_standings[1]['team'], self.mclaren)
        self.assertEqual(constructor_standings[1]['points'], Decimal('25'))
        self.assertEqual(constructor_standings[1]['position'], 2)

    def test_standings_snapshots(self):
        """Test standings progression snapshots and data extraction."""
        # Create results
        SessionResult.objects.create(race=self.race1, driver=self.norris, session_type='race', position=1, points=Decimal('25'))
        SessionResult.objects.create(race=self.race1, driver=self.leclerc, session_type='race', position=2, points=Decimal('18'))
        SessionResult.objects.create(race=self.race1, driver=self.hamilton, session_type='race', position=3, points=Decimal('15'))

        standings_service = StandingsService(season=2026)
        standings_service.create_standings_snapshot(round_number=1)

        snapshots = StandingsSnapshot.objects.filter(season=2026, round_number=1)
        # 3 drivers + 2 constructors = 5 snapshots
        self.assertEqual(snapshots.count(), 5)

        driver_snaps = snapshots.filter(snapshot_type='driver')
        self.assertEqual(driver_snaps.filter(driver=self.norris).first().points, Decimal('25'))
        self.assertEqual(driver_snaps.filter(driver=self.norris).first().position, 1)

        # Progression check
        progression = standings_service.get_points_progression(snapshot_type='driver')
        self.assertEqual(progression['labels'], ['R1'])
        self.assertEqual(len(progression['datasets']), 3)

    def test_prediction_scoring_exact_podium(self):
        """Test exact podium prediction scoring (max 15 points + 3 bonus = 18 points)."""
        # Note: actually, max is 15 points including bonus? Let's check:
        # P1 exact: 5
        # P2 exact: 4
        # P3 exact: 3
        # Exact podium bonus: 3
        # Total = 5+4+3+3 = 15 points.
        # Let's test this exact scenario.
        
        # Results
        SessionResult.objects.create(race=self.race1, driver=self.norris, session_type='race', position=1, points=Decimal('25'))
        SessionResult.objects.create(race=self.race1, driver=self.leclerc, session_type='race', position=2, points=Decimal('18'))
        SessionResult.objects.create(race=self.race1, driver=self.hamilton, session_type='race', position=3, points=Decimal('15'))

        # Prediction: Norris, Leclerc, Hamilton
        pred = Prediction.objects.create(
            user=self.user,
            race=self.race1,
            session_type='race',
            p1_driver=self.norris,
            p2_driver=self.leclerc,
            p3_driver=self.hamilton,
            is_locked=True
        )

        scorer = PredictionScorer()
        score = scorer.score_prediction(pred)

        self.assertIsNotNone(score)
        self.assertTrue(score.exact_p1)
        self.assertTrue(score.exact_p2)
        self.assertTrue(score.exact_p3)
        self.assertTrue(score.exact_podium_bonus)
        self.assertEqual(score.correct_drivers, 0)
        self.assertEqual(score.total_points, 15)

    def test_prediction_scoring_partial_matches(self):
        """Test prediction scoring with mixed matches and wrong positions."""
        # Results: Norris, Leclerc, Hamilton
        SessionResult.objects.create(race=self.race1, driver=self.norris, session_type='race', position=1, points=Decimal('25'))
        SessionResult.objects.create(race=self.race1, driver=self.leclerc, session_type='race', position=2, points=Decimal('18'))
        SessionResult.objects.create(race=self.race1, driver=self.hamilton, session_type='race', position=3, points=Decimal('15'))

        # Prediction: Leclerc (should be P2), Hamilton (should be P3), Norris (should be P1)
        # All correct drivers but all in wrong positions!
        # Points: 0 for exact positions, 3 correct wrong positions = 3 points.
        pred = Prediction.objects.create(
            user=self.user,
            race=self.race1,
            session_type='race',
            p1_driver=self.leclerc,
            p2_driver=self.hamilton,
            p3_driver=self.norris,
            is_locked=True
        )

        scorer = PredictionScorer()
        score = scorer.score_prediction(pred)

        self.assertIsNotNone(score)
        self.assertFalse(score.exact_p1)
        self.assertFalse(score.exact_p2)
        self.assertFalse(score.exact_p3)
        self.assertFalse(score.exact_podium_bonus)
        self.assertEqual(score.correct_drivers, 3)
        self.assertEqual(score.total_points, 3)

    def test_prediction_scoring_one_exact_one_wrong_pos(self):
        """Test scoring when one is exact and one is wrong position, and one is not in top 3."""
        # Results: Norris, Leclerc, Hamilton
        SessionResult.objects.create(race=self.race1, driver=self.norris, session_type='race', position=1, points=Decimal('25'))
        SessionResult.objects.create(race=self.race1, driver=self.leclerc, session_type='race', position=2, points=Decimal('18'))
        SessionResult.objects.create(race=self.race1, driver=self.hamilton, session_type='race', position=3, points=Decimal('15'))

        # Driver not in top 3: some other driver is not created, let's use Leclerc as predicted P2 (exact), Hamilton as P1 (wrong position), and Norris as not predicted (someone else predicted P3)
        # Let's create another driver (e.g. Verstappen)
        verstappen = Driver.objects.create(
            first_name='Max',
            last_name='Verstappen',
            abbreviation='VER',
            number=33,
            is_reserve=False,
            fastf1_driver_id='verstappen'
        )

        # Prediction: Hamilton (should be P3, so wrong position -> 1pt), Leclerc (should be P2, exact -> 4pt), Verstappen (not in actual top 3 -> 0pt)
        # Total points: 4 + 1 = 5 points
        pred = Prediction.objects.create(
            user=self.user,
            race=self.race1,
            session_type='race',
            p1_driver=self.hamilton,
            p2_driver=self.leclerc,
            p3_driver=verstappen,
            is_locked=True
        )

        scorer = PredictionScorer()
        score = scorer.score_prediction(pred)

        self.assertIsNotNone(score)
        self.assertFalse(score.exact_p1)
        self.assertTrue(score.exact_p2)
        self.assertFalse(score.exact_p3)
        self.assertEqual(score.correct_drivers, 1)
        self.assertEqual(score.total_points, 5)

    def test_get_leaderboard_and_head_to_head(self):
        """Test leaderboard and head-to-head helper utilities."""
        # Results
        SessionResult.objects.create(race=self.race1, driver=self.norris, session_type='race', position=1, points=Decimal('25'))
        SessionResult.objects.create(race=self.race1, driver=self.leclerc, session_type='race', position=2, points=Decimal('18'))
        SessionResult.objects.create(race=self.race1, driver=self.hamilton, session_type='race', position=3, points=Decimal('15'))

        # User 1 prediction (exact match -> 15 points)
        pred1 = Prediction.objects.create(
            user=self.user, race=self.race1, session_type='race',
            p1_driver=self.norris, p2_driver=self.leclerc, p3_driver=self.hamilton,
            is_locked=True
        )

        # User 2 prediction (completely wrong -> 0 points)
        verstappen = Driver.objects.create(
            first_name='Max', last_name='Verstappen', abbreviation='VER', number=33
        )
        pred2 = Prediction.objects.create(
            user=self.user2, race=self.race1, session_type='race',
            p1_driver=verstappen, p2_driver=verstappen, p3_driver=verstappen,
            is_locked=True
        )

        scorer = PredictionScorer()
        scorer.score_prediction(pred1)
        scorer.score_prediction(pred2)

        # Check leaderboard
        leaderboard = list(get_leaderboard(season=2026))
        self.assertEqual(len(leaderboard), 2)
        self.assertEqual(leaderboard[0]['user__username'], 'testuser')
        self.assertEqual(leaderboard[0]['total_pts'], 15)
        self.assertEqual(leaderboard[1]['user__username'], 'testuser2')
        self.assertEqual(leaderboard[1]['total_pts'], 0)

        # Check head-to-head
        h2h = get_head_to_head(self.user, self.user2, season=2026)
        self.assertEqual(h2h['user1']['username'], 'testuser')
        self.assertEqual(h2h['user1']['total'], 15)
        self.assertEqual(h2h['user1']['wins'], 1)
        self.assertEqual(h2h['user2']['username'], 'testuser2')
        self.assertEqual(h2h['user2']['total'], 0)
        self.assertEqual(h2h['user2']['wins'], 0)
