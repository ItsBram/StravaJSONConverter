# Strava JSON Converter

Export your Strava data to JSON for analysis with AI tools or custom processing.

## Features

- **OAuth Authentication** - Secure Strava API integration
- **Complete Data Export** - Activities, athlete profile, gear, routes, zones
- **Stream Data** - Time-indexed speed, elevation, heart rate, cadence, power
- **Smart Downsampling** - Reduces data size while preserving key moments
- **Background Sync** - Non-blocking data synchronization
- **SQLite Storage** - Local database, no external dependencies

## Requirements

- Python 3.9+
- A Strava account with API access

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file (use `.env.example` as template):

```env
SECRET_KEY=your-secret-key-here
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=http://localhost:5000/auth/callback
```

### Getting Strava API Credentials

1. Go to https://www.strava.com/settings/api
2. Create a new API application
3. Copy your Client ID and Client Secret
4. Set the Authorization Callback Domain to `localhost`

## Usage

1. Start the server:

```bash
python app.py
```

2. Open http://localhost:5000 in your browser

3. Click "Connect with Strava" and authorize

4. Your data will sync automatically. Export to JSON when complete.

## What Gets Exported

### Activities
- Distance, time, elevation
- Speed, heart rate, power, cadence
- Time-indexed stream data (20-second intervals)
- Gear used, workout type

### Athlete Profile
- Name, location, weight, FTP
- Heart rate and power zones

### Gear
- Bikes and shoes with mileage

### Routes
- Saved routes with map data

## Stream Data Format

Each activity includes a `records` array with data points every 20 seconds:

```json
{
  "elapsed_seconds": 0,
  "distance_m": 120.5,
  "altitude_m": 15.2,
  "speed_ms": 5.3,
  "speed_kmh": 19.1,
  "heartrate_bpm": 125,
  "cadence_rpm": 85,
  "power_watts": 210,
  "grade_percent": 2.1
}
```

## Rate Limiting

This app respects Strava's API limits:
- 100 requests per 15 minutes
- ~9 second delay between requests
- Automatic token refresh

## Development

To start fresh (delete all data):

```bash
rm -f strava_data.db
```

To debug database contents, visit http://localhost:5000/debug while logged in.

## License

MIT License - feel free to use and modify.

## Support

For issues or questions, please open an issue on GitHub.
