# 🏎️ F1 Predictor

> A premium Formula 1 prediction and analytics platform for the 2026 season.

![Python](https://img.shields.io/badge/Python-3.12-blue) ![Django](https://img.shields.io/badge/Django-5.1-green) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Overview

F1 Predictor is a full-featured web application that lets you and your friends predict Formula 1 race results, track the championship, and compare prediction accuracy throughout the 2026 season. It syncs real F1 data automatically using FastF1 and the Jolpica API.

### Key Features

- 🏁 **Real F1 Data** — Automatic syncing of schedules, results, and standings via FastF1
- 🎯 **Prediction System** — Predict qualifying, sprint, and race top 3 with drag-and-drop UI
- 📊 **Scoring Engine** — Automatic scoring with exact position, correct driver, and podium bonus points
- 📈 **Analytics Dashboard** — Points progression, accuracy charts, and user comparisons
- 👥 **Head-to-Head** — Compare predictions with friends race by race
- 🔄 **Driver Swap Support** — Full mid-season replacement tracking in the database
- 🎨 **Premium Dark UI** — F1-inspired glassmorphism design with team colors and animations
- 📱 **Fully Responsive** — Works beautifully on desktop, tablet, and mobile
- ⚙️ **Admin Panel** — Full CRUD for drivers, teams, races, results, and scores

---

## Architecture

```
f1predictor/
├── manage.py                    # Django management
├── requirements.txt             # Python dependencies
├── render.yaml                  # Render deployment
├── Procfile                     # Process definitions
├── runtime.txt                  # Python version
├── .env.example                 # Environment template
│
├── f1predictor/                 # Project configuration
│   ├── settings/
│   │   ├── base.py              # Shared settings
│   │   ├── development.py       # SQLite, DEBUG=True
│   │   └── production.py        # PostgreSQL, security
│   ├── celery.py                # Celery + Beat schedule
│   ├── urls.py                  # Root URL config
│   ├── wsgi.py / asgi.py
│
├── core/                        # Main application
│   ├── models.py                # 10+ database models
│   ├── admin.py                 # Full admin panel
│   ├── forms.py                 # Auth & profile forms
│   ├── views/                   # View modules
│   │   ├── dashboard.py
│   │   ├── standings.py
│   │   ├── races.py
│   │   ├── predictions.py
│   │   ├── analytics.py
│   │   └── auth.py
│   ├── services/                # Business logic
│   │   ├── fastf1_sync.py       # FastF1 data syncing
│   │   ├── scoring.py           # Prediction scoring
│   │   └── standings.py         # Standings calculation
│   ├── api/                     # REST API (DRF)
│   │   ├── views.py
│   │   └── urls.py
│   ├── tasks.py                 # Celery tasks
│   ├── management/commands/     # CLI commands
│   ├── templatetags/f1_tags.py  # Custom template tags
│   └── context_processors.py
│
├── templates/                   # Django templates
│   ├── base.html                # Master layout
│   ├── dashboard/               # Dashboard
│   ├── standings/               # Driver & constructor standings
│   ├── races/                   # Calendar & race detail
│   ├── predictions/             # Make predictions, results, leaderboard
│   ├── analytics/               # Charts & analytics
│   ├── auth/                    # Login, signup, profile
│   ├── components/              # Reusable UI components
│   └── partials/                # HTMX partial templates
│
├── static/
│   ├── css/input.css            # Tailwind CSS source
│   └── js/
│       ├── app.js               # Main app JS
│       ├── predictions.js       # Drag-and-drop
│       ├── charts.js            # Chart.js configs
│       └── countdown.js         # Race countdown
│
└── media/                       # User uploads
```

---

## Setup Instructions

### Prerequisites

- Python 3.12+
- pip
- Git
- Redis (for Celery — optional for development)

### 1. Clone & Virtual Environment

```bash
git clone <repository-url> f1predictor
cd f1predictor

# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your settings (the defaults work for development)
```

### 4. Database Setup

**Development (SQLite — no setup needed):**

```bash
python manage.py migrate
```

**Production (PostgreSQL):**

```bash
# Install PostgreSQL and create database
createdb f1predictor

# Set DATABASE_URL in .env
DATABASE_URL=postgres://user:password@localhost:5432/f1predictor

# Run migrations
DJANGO_SETTINGS_MODULE=f1predictor.settings.production python manage.py migrate
```

### 5. Create Admin User

```bash
python manage.py createsuperuser
```

### 6. Seed 2026 Season Data

```bash
# This seeds all 11 teams, 22 drivers, and syncs the race schedule
python manage.py seed_2026
```

### 7. Compile Tailwind CSS

Using `django-tailwind-cli`:

```bash
pip install django-tailwind-cli
python manage.py tailwind build
```

Or manually download Tailwind standalone CLI:

```bash
# Download from https://github.com/tailwindlabs/tailwindcss/releases
# Then run:
./tailwindcss -i static/css/input.css -o static/css/output.css --minify
```

For development with hot-reload:

```bash
./tailwindcss -i static/css/input.css -o static/css/output.css --watch
```

### 8. Run Development Server

```bash
python manage.py runserver
```

Visit: **http://localhost:8000**

---

## FastF1 Setup

### Cache Configuration

FastF1 caches downloaded session data locally to avoid API rate limits (~500 calls/hour).

```bash
# Default cache directory (configured in settings)
FASTF1_CACHE_DIR=./fastf1_cache

# The cache is created automatically on first sync
# Typical session data: 50-100MB per session
```

### Syncing Data

```bash
# Full sync (schedule + results + standings)
python manage.py sync_f1_data --full

# Sync schedule only
python manage.py sync_f1_data --schedule

# Sync specific race results
python manage.py sync_f1_data --race 5

# Sync standings only
python manage.py sync_f1_data --standings
```

---

## Celery Setup (Automatic Syncing)

### 1. Install Redis

```bash
# macOS
brew install redis && brew services start redis

# Ubuntu/Debian
sudo apt install redis-server

# Windows
# Download from https://github.com/microsoftarchive/redis/releases
# Or use Docker: docker run -d -p 6379:6379 redis
```

### 2. Start Celery Worker

```bash
celery -A f1predictor worker --loglevel=info
```

### 3. Start Celery Beat (Scheduler)

```bash
celery -A f1predictor beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Automatic Sync Schedule

| Task | Schedule | Description |
|------|----------|-------------|
| `sync_season_schedule` | Daily at 6 AM UTC | Update race calendar |
| `sync_latest_results` | Every hour | Fetch new results |
| `sync_standings` | Daily at 7 AM UTC | Update championship standings |
| `lock_expired_predictions` | Every 15 minutes | Auto-lock predictions |
| `score_all_pending` | Every 2 hours | Score unscored predictions |

---

## Prediction Scoring

### Rules

| Condition | Points |
|-----------|--------|
| Exact P1 prediction | 5 |
| Exact P2 prediction | 4 |
| Exact P3 prediction | 3 |
| Correct driver, wrong position | 1 each |
| Exact podium bonus (all 3 correct) | 3 bonus |
| **Maximum per session** | **15** |

### Per Race Weekend

- Non-sprint: Qualifying + Race = **30 max**
- Sprint weekend: Qualifying + Sprint + Race = **45 max**

### Score Predictions Manually

```bash
# Score all pending predictions
python manage.py score_predictions

# Score specific race
python manage.py score_predictions --race 5

# Re-score all predictions
python manage.py score_predictions --rescore
```

---

## Admin Panel

Access: **http://localhost:8000/admin/**

### Capabilities

- **Teams**: Add/edit/remove teams, set colors, upload logos
- **Drivers**: Manage drivers, numbers, reserve status, headshots
- **Driver Team History**: Track mid-season swaps with date ranges
- **Races**: Edit schedules, toggle sprint weekends, set status
- **Session Results**: View/override qualifying, sprint, and race results
- **Predictions**: View, lock/unlock user predictions
- **Prediction Scores**: View scores, recalculate with one click
- **User Profiles**: Manage users and their favorite teams

### Custom Actions

- Mark races as completed/upcoming
- Toggle sprint weekend status
- Lock/unlock predictions in bulk
- Recalculate prediction scores

---

## How to Handle Driver Switches

The `DriverTeamHistory` model tracks all team assignments:

1. Go to **Admin → Driver Team Assignments**
2. Find the departing driver's current assignment
3. Set `date_to` to the replacement date and `is_active = False`
4. Create a new assignment for the replacement driver with `date_from` set to the replacement date

All historical results are preserved — they reference the Driver, not the team assignment.

---

## Deployment

### Render (Recommended)

1. Push code to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo
4. Render will use `render.yaml` to create services automatically
5. After deployment:

```bash
# SSH into Render shell or use the Dashboard console
python manage.py createsuperuser
python manage.py seed_2026
```

### Railway

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → New Project
3. Deploy from GitHub repo
4. Add PostgreSQL and Redis plugins
5. Set environment variables:

```
DJANGO_SETTINGS_MODULE=f1predictor.settings.production
SECRET_KEY=<generated>
ALLOWED_HOSTS=.railway.app
DATABASE_URL=<from Railway PostgreSQL>
REDIS_URL=<from Railway Redis>
```

### Static & Media Files

- **Static files**: Served by WhiteNoise (built into middleware)
- **Media files (uploads)**: For production, consider:
  - AWS S3 with `django-storages`
  - Cloudinary
  - Render's persistent disk

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_SETTINGS_MODULE` | `f1predictor.settings.development` | Settings module |
| `SECRET_KEY` | (dev key) | Django secret key |
| `DEBUG` | `True` | Debug mode |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Allowed hostnames |
| `DATABASE_URL` | SQLite | Database connection URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for Celery |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker URL |
| `FASTF1_CACHE_DIR` | `./fastf1_cache` | FastF1 cache directory |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Django 5.1, Django REST Framework |
| Frontend | Django Templates, HTMX, Alpine.js |
| Styling | Tailwind CSS v4 |
| Charts | Chart.js 4 |
| Drag & Drop | SortableJS |
| Data Source | FastF1, Jolpica API |
| Task Queue | Celery, Celery Beat, Redis |
| Database | SQLite (dev), PostgreSQL (prod) |
| Static Files | WhiteNoise |
| Deployment | Render, Railway |

---

## Future Improvements

- [ ] WebSocket live updates with Django Channels
- [ ] Telemetry visualization overlays
- [ ] Lap comparison tool
- [ ] Tyre strategy visualization charts
- [ ] PWA (Progressive Web App) with offline support
- [ ] Push notifications for race reminders
- [ ] Achievement/badge system
- [ ] Dark/light mode toggle
- [ ] Social sharing of predictions
- [ ] Season history (2025, 2024 archives)
- [ ] Multi-language support
- [ ] Email notifications

---

## License

MIT License. Built with ❤️ for F1 fans.
