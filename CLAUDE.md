# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the development server
python app.py

# Delete database and start fresh (useful during development)
rm -f strava_data.db

# Check what's in the database (debug endpoint after running)
# Visit http://localhost:5000/debug while logged in
```

## Architecture Overview

This is a Flask web application that fetches Strava data via OAuth and exports it as JSON for AI analysis.

### Application Bootstrap

- **Entry point**: `app.py` uses an application factory pattern (`create_app()`)
- **Database**: SQLAlchemy with `db` instance defined in `extensions.py` (not `app.py`) to avoid circular imports
- **Background tasks**: `DataFetcher` uses threading; requires `DataFetcher.set_app(app)` to be called during app initialization for Flask context in background threads

### Data Flow

1. **OAuth Flow** (`routes/auth_routes.py`):
   - User enters Client ID/Secret → stored in `current_app.config`
   - Redirect to Strava → callback receives `code` → exchanges for tokens
   - Tokens stored in `Athlete` model (access_token, refresh_token, expires_at)
   - Auto-triggers `DataFetcher.start_sync()` on first connection

2. **Data Synchronization** (`services/data_fetcher.py`):
   - Runs in daemon thread with Flask app context
   - Paginated fetching (200 items per page)
   - Progress tracked via `SyncJob` model in database
   - Rate limited to 1.5s between requests (~40 req/min)

3. **Export** (`services/export_service.py`):
   - Queries all models and structures JSON
   - Includes calculated statistics
   - Designed for AI consumption (training plans, analysis)

### Important Architecture Decisions

- **Stream data disabled by default**: Activity streams (detailed GPS/sensor time-series) are NOT fetched to conserve API calls. The main activity data already contains distance, time, heart rate, power, elevation, etc. Re-enable in `_fetch_activity_details()` if needed.

- **Thread-based background tasks**: Uses simple threading, not Celery. Each sync runs in a daemon thread. Suitable for single-user scenarios.

- **Token refresh handled automatically**: `StravaClient._get_token()` checks expiry and refreshes tokens transparently.

- **Raw JSON preserved**: All models have `raw_data_json` field storing complete Strava API response for debugging/future use.

- **SQLite for simplicity**: Database file is `strava_data.db`. Can switch to PostgreSQL/MySQL via `SQLALCHEMY_DATABASE_URI` in `config.py`.

### Rate Limiting

Strava allows ~600 requests per 15 minutes for authenticated users. This app implements client-side rate limiting at 1.5 seconds between requests in `StravaClient._rate_limit()`.

### Models and Relationships

- **Athlete**: Central entity, has many Activities, Gear, Routes, Zones, SyncJobs
- **Activity**: Detailed metrics (distance, time, HR, power, elevation, etc.)
- **Gear**: Bikes and shoes with distance tracking
- **Route**: Saved routes with map polylines
- **SyncJob**: Tracks background sync progress and errors

All models use cascade delete relationships.

### Environment Configuration

Required environment variables (see `.env.example`):
- `SECRET_KEY`: Flask session encryption
- `STRAVA_CLIENT_ID`: From Strava API settings
- `STRAVA_CLIENT_SECRET`: From Strava API settings
- `STRAVA_REDIRECT_URI`: Must match Strava app settings (default: `http://localhost:5000/auth/callback`)
