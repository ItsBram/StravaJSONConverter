# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Stack

- **Python** is the primary language for this project
- When adding new features, follow existing patterns in the codebase for configuration, API calls, and error handling

## Strava API Conventions

- Valid resolution parameters for streams: `low`, `medium`, `high` (never use `all`)
- Always verify that methods referenced elsewhere in the code are not removed during refactoring
- Stream data is only available for activities recorded with sensors (GPS, heart rate, etc.); handle missing streams gracefully

## Refactoring Rules

- Before deleting any function or method, search for all references across the entire codebase using grep or file search
- After refactoring, run the application and verify no import or attribute errors occur

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
   - App uses pre-configured Client ID/Secret from `.env` (loaded via `config.py`)
   - User clicks "Connect with Strava" → redirect to Strava → callback receives `code` → exchanges for tokens
   - Tokens stored in `Athlete` model (access_token, refresh_token, expires_at)
   - Auto-triggers `DataFetcher.start_sync()` on first connection

2. **Data Synchronization** (`services/data_fetcher.py`):
   - Runs in daemon thread with Flask app context
   - Paginated fetching (200 items per page)
   - Progress tracked via `SyncJob` model in database
   - Rate limited to 9.0s between requests (~100 req per 15 min)
   - Fetches activities from the last year only

3. **Export** (`services/export_service.py`):
   - Queries all models and structures JSON
   - Uses eager loading (`joinedload`) for streams to avoid lazy loading issues
   - Includes calculated statistics
   - Designed for AI consumption (training plans, analysis)

### Important Architecture Decisions

- **Stream data always fetched**: Activity streams (time-indexed speed, elevation, HR, power, etc.) are fetched for ALL activities, not just those with HR/power sensors. Streams are downsampled to 20-second intervals to keep data manageable while preserving peaks.

- **Thread-based background tasks**: Uses simple threading, not Celery. Each sync runs in a daemon thread. Suitable for single-user scenarios.

- **Token refresh handled automatically**: `StravaClient._get_token()` checks expiry and refreshes tokens transparently.

- **Raw JSON NOT preserved**: Unlike some implementations, raw JSON from Strava is NOT stored in the database to save space. Only training-relevant fields are stored.

- **SQLite for simplicity**: Database file is `strava_data.db`. Can switch to PostgreSQL/MySQL via `SQLALCHEMY_DATABASE_URI` in `config.py`.

- **Robust error handling**: Individual activity failures don't stop the entire sync. Failed activities are logged and skipped.

### Stream Data Format

Streams are stored as `ActivityStream` records with `stream_type='records'`. Each activity's `records` array contains time-indexed data points (20-second intervals):

```python
{
    "elapsed_seconds": 0,      # Time since activity start
    "distance_m": 120.5,       # Cumulative distance in meters
    "altitude_m": 15.2,        # Elevation in meters
    "speed_ms": 5.3,           # Speed in m/s
    "speed_kmh": 19.1,         # Speed in km/h (derived)
    "heartrate_bpm": 125,      # Heart rate (null if not available)
    "cadence_rpm": 85,         # Cadence (null if not available)
    "power_watts": 210,        # Power (null if not available)
    "grade_percent": 2.1       # Road grade (null if not available)
}
```

The downsampling algorithm keeps:
- Every 20th point (regular interval)
- First and last points
- Peak values (max HR, max speed, max power)

### Rate Limiting

Strava allows 100 requests per 15 minutes for authenticated users. This app implements client-side rate limiting at 9.0 seconds between requests in `StravaClient._rate_limit()`.

If streams fail with 400 error, the client falls back to simpler stream type combinations (removing grade_smooth, then cadence/watts).

### Models and Relationships

- **Athlete**: Central entity, has many Activities, Gear, Routes, Zones, SyncJobs
- **Activity**: Detailed metrics (distance, time, HR, power, elevation, etc.) with has-many ActivityStream
- **ActivityStream**: Time-series stream data (records array)
- **Gear**: Bikes and shoes with distance tracking
- **Route**: Saved routes with map polylines
- **SyncJob**: Tracks background sync progress and errors
- **AthleteZone**: Heart rate and power zones

All models use cascade delete relationships.

### Environment Configuration

Server environment variables — configured by the operator in `.env` or server environment (see `.env.example`):
- `SECRET_KEY`: Flask session encryption (MUST be changed for production)
- `STRAVA_CLIENT_ID`: Strava API Client ID (pre-configured by operator)
- `STRAVA_CLIENT_SECRET`: Strava API Client Secret (pre-configured by operator)
- `STRAVA_REDIRECT_URI`: Must match Strava app settings (default: `http://localhost:5000/auth/callback`)

These are server-side credentials shared by all users. End users do NOT need their own Strava API applications — they simply visit the site and click "Connect with Strava". The app will refuse to start if credentials are missing.
