"""
Seed the 2026 F1 season with real schedule and driver data.
No external API dependencies required.
"""
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Team, Driver, DriverTeamHistory, Race


TEAMS = [
    {"name": "Red Bull Racing", "short_name": "Red Bull", "color_primary": "#3671C6", "color_secondary": "#1B2A4A", "constructor_id": "red_bull"},
    {"name": "McLaren", "short_name": "McLaren", "color_primary": "#FF8000", "color_secondary": "#47290A", "constructor_id": "mclaren"},
    {"name": "Scuderia Ferrari", "short_name": "Ferrari", "color_primary": "#E8002D", "color_secondary": "#4A000E", "constructor_id": "ferrari"},
    {"name": "Mercedes-AMG Petronas", "short_name": "Mercedes", "color_primary": "#27F4D2", "color_secondary": "#0A4A3E", "constructor_id": "mercedes"},
    {"name": "Aston Martin Aramco", "short_name": "Aston Martin", "color_primary": "#229971", "color_secondary": "#0D3D2D", "constructor_id": "aston_martin"},
    {"name": "Williams Racing", "short_name": "Williams", "color_primary": "#64C4FF", "color_secondary": "#1E3A4F", "constructor_id": "williams"},
    {"name": "Alpine F1 Team", "short_name": "Alpine", "color_primary": "#FF87BC", "color_secondary": "#4A2838", "constructor_id": "alpine"},
    {"name": "MoneyGram Haas F1 Team", "short_name": "Haas", "color_primary": "#B6BABD", "color_secondary": "#3A3B3D", "constructor_id": "haas"},
    {"name": "Racing Bulls", "short_name": "Racing Bulls", "color_primary": "#6692FF", "color_secondary": "#1E2D4F", "constructor_id": "rb"},
    {"name": "Audi", "short_name": "Audi", "color_primary": "#00E701", "color_secondary": "#004A00", "constructor_id": "audi"},
    {"name": "Cadillac F1 Team", "short_name": "Cadillac", "color_primary": "#FFD700", "color_secondary": "#4A3E00", "constructor_id": "cadillac"},
]

DRIVERS = [
    # Red Bull
    {"first_name": "Max", "last_name": "Verstappen", "abbreviation": "VER", "number": 1, "country": "Netherlands", "team": "Red Bull"},
    {"first_name": "Liam", "last_name": "Lawson", "abbreviation": "LAW", "number": 30, "country": "New Zealand", "team": "Red Bull"},
    # McLaren
    {"first_name": "Lando", "last_name": "Norris", "abbreviation": "NOR", "number": 4, "country": "United Kingdom", "team": "McLaren"},
    {"first_name": "Oscar", "last_name": "Piastri", "abbreviation": "PIA", "number": 81, "country": "Australia", "team": "McLaren"},
    # Ferrari
    {"first_name": "Charles", "last_name": "Leclerc", "abbreviation": "LEC", "number": 16, "country": "Monaco", "team": "Ferrari"},
    {"first_name": "Lewis", "last_name": "Hamilton", "abbreviation": "HAM", "number": 44, "country": "United Kingdom", "team": "Ferrari"},
    # Mercedes
    {"first_name": "George", "last_name": "Russell", "abbreviation": "RUS", "number": 63, "country": "United Kingdom", "team": "Mercedes"},
    {"first_name": "Andrea", "last_name": "Kimi Antonelli", "abbreviation": "ANT", "number": 12, "country": "Italy", "team": "Mercedes"},
    # Aston Martin
    {"first_name": "Fernando", "last_name": "Alonso", "abbreviation": "ALO", "number": 14, "country": "Spain", "team": "Aston Martin"},
    {"first_name": "Lance", "last_name": "Stroll", "abbreviation": "STR", "number": 18, "country": "Canada", "team": "Aston Martin"},
    # Williams
    {"first_name": "Carlos", "last_name": "Sainz", "abbreviation": "SAI", "number": 55, "country": "Spain", "team": "Williams"},
    {"first_name": "Alexander", "last_name": "Albon", "abbreviation": "ALB", "number": 23, "country": "Thailand", "team": "Williams"},
    # Alpine
    {"first_name": "Pierre", "last_name": "Gasly", "abbreviation": "GAS", "number": 10, "country": "France", "team": "Alpine"},
    {"first_name": "Jack", "last_name": "Doohan", "abbreviation": "DOO", "number": 7, "country": "Australia", "team": "Alpine"},
    # Haas
    {"first_name": "Esteban", "last_name": "Ocon", "abbreviation": "OCO", "number": 31, "country": "France", "team": "Haas"},
    {"first_name": "Oliver", "last_name": "Bearman", "abbreviation": "BEA", "number": 87, "country": "United Kingdom", "team": "Haas"},
    # Racing Bulls
    {"first_name": "Yuki", "last_name": "Tsunoda", "abbreviation": "TSU", "number": 22, "country": "Japan", "team": "Racing Bulls"},
    {"first_name": "Isack", "last_name": "Hadjar", "abbreviation": "HAD", "number": 6, "country": "France", "team": "Racing Bulls"},
    # Audi (Sauber rebranded)
    {"first_name": "Nico", "last_name": "Hulkenberg", "abbreviation": "HUL", "number": 27, "country": "Germany", "team": "Audi"},
    {"first_name": "Gabriel", "last_name": "Bortoleto", "abbreviation": "BOR", "number": 5, "country": "Brazil", "team": "Audi"},
    # Cadillac
    {"first_name": "Valtteri", "last_name": "Bottas", "abbreviation": "BOT", "number": 77, "country": "Finland", "team": "Cadillac"},
    {"first_name": "Theo", "last_name": "Pourchaire", "abbreviation": "POU", "number": 13, "country": "France", "team": "Cadillac"},
]

RACES_2026 = [
    {"round": 1, "name": "Australian Grand Prix", "country": "Australia", "city": "Melbourne", "circuit": "Albert Park Circuit", "date": "2026-03-15T05:00:00Z", "sprint": False},
    {"round": 2, "name": "Chinese Grand Prix", "country": "China", "city": "Shanghai", "circuit": "Shanghai International Circuit", "date": "2026-03-29T07:00:00Z", "sprint": True},
    {"round": 3, "name": "Japanese Grand Prix", "country": "Japan", "city": "Suzuka", "circuit": "Suzuka International Racing Course", "date": "2026-04-05T06:00:00Z", "sprint": False},
    {"round": 4, "name": "Bahrain Grand Prix", "country": "Bahrain", "city": "Sakhir", "circuit": "Bahrain International Circuit", "date": "2026-04-12T15:00:00Z", "sprint": False},
    {"round": 5, "name": "Saudi Arabian Grand Prix", "country": "Saudi Arabia", "city": "Jeddah", "circuit": "Jeddah Corniche Circuit", "date": "2026-04-19T17:00:00Z", "sprint": False},
    {"round": 6, "name": "Miami Grand Prix", "country": "United States", "city": "Miami", "circuit": "Miami International Autodrome", "date": "2026-05-03T19:00:00Z", "sprint": True},
    {"round": 7, "name": "Emilia Romagna Grand Prix", "country": "Italy", "city": "Imola", "circuit": "Autodromo Enzo e Dino Ferrari", "date": "2026-05-17T13:00:00Z", "sprint": False},
    {"round": 8, "name": "Monaco Grand Prix", "country": "Monaco", "city": "Monte Carlo", "circuit": "Circuit de Monaco", "date": "2026-05-24T13:00:00Z", "sprint": False},
    {"round": 9, "name": "Spanish Grand Prix", "country": "Spain", "city": "Barcelona", "circuit": "Circuit de Barcelona-Catalunya", "date": "2026-06-07T13:00:00Z", "sprint": False},
    {"round": 10, "name": "Canadian Grand Prix", "country": "Canada", "city": "Montreal", "circuit": "Circuit Gilles Villeneuve", "date": "2026-06-14T18:00:00Z", "sprint": False},
    {"round": 11, "name": "Austrian Grand Prix", "country": "Austria", "city": "Spielberg", "circuit": "Red Bull Ring", "date": "2026-06-28T13:00:00Z", "sprint": True},
    {"round": 12, "name": "British Grand Prix", "country": "United Kingdom", "city": "Silverstone", "circuit": "Silverstone Circuit", "date": "2026-07-05T14:00:00Z", "sprint": False},
    {"round": 13, "name": "Belgian Grand Prix", "country": "Belgium", "city": "Spa", "circuit": "Circuit de Spa-Francorchamps", "date": "2026-07-26T13:00:00Z", "sprint": False},
    {"round": 14, "name": "Hungarian Grand Prix", "country": "Hungary", "city": "Budapest", "circuit": "Hungaroring", "date": "2026-08-02T13:00:00Z", "sprint": False},
    {"round": 15, "name": "Dutch Grand Prix", "country": "Netherlands", "city": "Zandvoort", "circuit": "Circuit Zandvoort", "date": "2026-08-30T13:00:00Z", "sprint": False},
    {"round": 16, "name": "Italian Grand Prix", "country": "Italy", "city": "Monza", "circuit": "Autodromo Nazionale Monza", "date": "2026-09-06T13:00:00Z", "sprint": False},
    {"round": 17, "name": "Azerbaijan Grand Prix", "country": "Azerbaijan", "city": "Baku", "circuit": "Baku City Circuit", "date": "2026-09-20T11:00:00Z", "sprint": False},
    {"round": 18, "name": "Singapore Grand Prix", "country": "Singapore", "city": "Singapore", "circuit": "Marina Bay Street Circuit", "date": "2026-10-04T12:00:00Z", "sprint": False},
    {"round": 19, "name": "United States Grand Prix", "country": "United States", "city": "Austin", "circuit": "Circuit of the Americas", "date": "2026-10-18T19:00:00Z", "sprint": True},
    {"round": 20, "name": "Mexican Grand Prix", "country": "Mexico", "city": "Mexico City", "circuit": "Autodromo Hermanos Rodriguez", "date": "2026-10-25T20:00:00Z", "sprint": False},
    {"round": 21, "name": "Brazilian Grand Prix", "country": "Brazil", "city": "Sao Paulo", "circuit": "Autodromo Jose Carlos Pace", "date": "2026-11-08T17:00:00Z", "sprint": True},
    {"round": 22, "name": "Las Vegas Grand Prix", "country": "United States", "city": "Las Vegas", "circuit": "Las Vegas Street Circuit", "date": "2026-11-22T06:00:00Z", "sprint": False},
    {"round": 23, "name": "Qatar Grand Prix", "country": "Qatar", "city": "Lusail", "circuit": "Lusail International Circuit", "date": "2026-11-29T14:00:00Z", "sprint": True},
    {"round": 24, "name": "Abu Dhabi Grand Prix", "country": "Abu Dhabi", "city": "Yas Marina", "circuit": "Yas Marina Circuit", "date": "2026-12-06T13:00:00Z", "sprint": False},
]


class Command(BaseCommand):
    help = "Seed 2026 F1 season data (teams, drivers, races) without external APIs"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("\n  Seeding 2026 F1 Season Data\n"))
        season_start = datetime(2026, 3, 1).date()

        # Teams
        team_map = {}
        for t in TEAMS:
            team, created = Team.objects.update_or_create(
                constructor_id=t["constructor_id"],
                defaults={
                    "name": t["name"],
                    "short_name": t["short_name"],
                    "color_primary": t["color_primary"],
                    "color_secondary": t["color_secondary"],
                    "is_active": True,
                },
            )
            team_map[t["short_name"]] = team
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status} team: {team.name}")

        # Drivers
        for d in DRIVERS:
            driver, created = Driver.objects.update_or_create(
                abbreviation=d["abbreviation"],
                defaults={
                    "first_name": d["first_name"],
                    "last_name": d["last_name"],
                    "number": d["number"],
                    "country": d["country"],
                },
            )
            team = team_map[d["team"]]
            DriverTeamHistory.objects.update_or_create(
                driver=driver,
                team=team,
                season=2026,
                date_from=season_start,
                defaults={"is_active": True},
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status} driver: {driver.full_name} -> {team.short_name}")

        # Races
        for r in RACES_2026:
            race_dt = datetime.fromisoformat(r["date"].replace("Z", "+00:00"))
            race, created = Race.objects.update_or_create(
                season=2026,
                round_number=r["round"],
                defaults={
                    "name": r["name"],
                    "country": r["country"],
                    "city": r["city"],
                    "circuit_name": r["circuit"],
                    "race_date": race_dt,
                    "has_sprint": r["sprint"],
                    "status": "completed" if race_dt < timezone.now() else "upcoming",
                    "is_completed": race_dt < timezone.now(),
                },
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status} race: R{r['round']} {r['name']}")

        self.stdout.write(self.style.SUCCESS(
            f"\n  Done! {Team.objects.count()} teams, "
            f"{Driver.objects.count()} drivers, "
            f"{Race.objects.count()} races\n"
        ))
