import requests
import time
from models.athlete import Athlete
from models.sync_job import SyncJob
from extensions import db


class StravaClient:
    BASE_URL = "https://www.strava.com/api/v3"

    def __init__(self, athlete_id):
        self.athlete_id = athlete_id
        self.access_token = None
        self._last_request_time = 0
        self._min_request_interval = 9.0  # 100 requests per 15 minutes = Strava's limit

    def _get_token(self):
        if not self.access_token:
            athlete = Athlete.query.get(self.athlete_id)
            if not athlete:
                raise ValueError(f"Athlete {self.athlete_id} not found")

            from datetime import datetime, timedelta
            expires_at = datetime.fromtimestamp(athlete.token_expires_at)

            if expires_at < datetime.now() + timedelta(hours=1):
                from api.oauth import StravaOAuth
                token_data = StravaOAuth.refresh_access_token(athlete.refresh_token)
                athlete.access_token = token_data['access_token']
                athlete.refresh_token = token_data['refresh_token']
                athlete.token_expires_at = token_data['expires_at']
                db.session.commit()
                self.access_token = token_data['access_token']
            else:
                self.access_token = athlete.access_token

        return self.access_token

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _request(self, method, endpoint, params=None, data=None):
        self._rate_limit()
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {'Authorization': f"Bearer {self._get_token()}"}

        response = requests.request(method, url, headers=headers, params=params, json=data)
        response.raise_for_status()
        return response.json()

    def get_athlete(self):
        return self._request('GET', 'athlete')

    def get_activities(self, page=1, per_page=30, before=None, after=None):
        params = {'page': page, 'per_page': per_page}
        if before:
            params['before'] = before
        if after:
            params['after'] = after
        return self._request('GET', 'athlete/activities', params=params)

    def get_activity(self, activity_id):
        return self._request('GET', f'activities/{activity_id}')

    def get_activity_zones(self, activity_id):
        try:
            return self._request('GET', f'activities/{activity_id}/zones')
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                return []
            raise

    def get_activity_streams(self, activity_id, types=None):
        """
        Fetch key stream types for training analysis.

        Priority: time, speed (velocity), elevation, then HR, cadence, power, etc.
        Uses 'resolution=high' for detailed data, then downsamples to 20s intervals.

        Returns: List of time-indexed records with combined stream data.
        """
        # Core streams: time (anchor), speed (velocity), elevation (altitude)
        # Optional: distance, HR, cadence, power, grade
        stream_variants = [
            "time,velocity_smooth,altitude,distance,heartrate,cadence,watts,grade_smooth",
            "time,velocity_smooth,altitude,distance,heartrate,cadence,watts",
            "time,velocity_smooth,altitude,distance"
        ]

        for i, stream_types in enumerate(stream_variants):
            try:
                params = {
                    'keys': stream_types
                }

                if i > 0:
                    print(f"    [RETRY] Attempt {i+1}: {stream_types}")

                response = self._request('GET', f'activities/{activity_id}/streams', params=params)
                print(f"    [STREAMS] Got {len(response)} streams")
                return self._parse_streams_to_records(response)
            except requests.HTTPError as e:
                if e.response.status_code == 400:
                    if i < len(stream_variants) - 1:
                        continue
                    print(f"    [ERROR] All stream attempts failed for activity {activity_id}")
                    return {}
                raise

    def _parse_streams_to_records(self, streams_data):
        """
        Parse Strava stream response (list format) into time-indexed records.

        Stream format: [ {"type": "time", "data": [...]}, {"type": "velocity_smooth", "data": [...]}, ... ]
        Output: List of records indexed by time with all available metrics.
        """
        if not streams_data:
            return []

        # Parse list of stream objects into dict
        streams = {}
        for stream_obj in streams_data:
            if isinstance(stream_obj, dict) and 'type' in stream_obj and 'data' in stream_obj:
                streams[stream_obj['type']] = stream_obj['data']

        # Time stream is required as anchor
        time_stream = streams.get('time', [])
        if not time_stream:
            return []

        # Build records
        records = []
        for i, t in enumerate(time_stream):
            record = {
                'elapsed_seconds': t,
                'distance_m': _get_safe(streams.get('distance'), i),
                'altitude_m': _get_safe(streams.get('altitude'), i),
                'speed_ms': _get_safe(streams.get('velocity_smooth'), i),
                'heartrate_bpm': _get_safe(streams.get('heartrate'), i),
                'cadence_rpm': _get_safe(streams.get('cadence'), i),
                'power_watts': _get_safe(streams.get('watts'), i),
                'grade_percent': _get_safe(streams.get('grade_smooth'), i)
            }
            # Derive speed_kmh
            if record['speed_ms'] is not None:
                record['speed_kmh'] = record['speed_ms'] * 3.6
            else:
                record['speed_kmh'] = None

            records.append(record)

        return records

    def downsample_records(self, records, interval_seconds=20):
        """
        Downsample time-indexed records to reduce data size while preserving key information.

        Strategy:
        - Keep every Nth point (where N = interval_seconds)
        - Always keep: first point, last point
        - Always keep: peak values (max HR, max speed, max power)

        Args:
            records: List of time-indexed records
            interval_seconds: Target interval between kept points

        Returns:
            Downsampled list of records
        """
        if not records or len(records) <= 10:
            return records

        interval_points = interval_seconds  # Since time stream is in seconds

        # Always include first point
        downsampled = [records[0]]

        # Track indices of key points to include
        max_hr_idx = 0
        max_speed_idx = 0
        max_power_idx = 0

        # Find peak indices
        for i, record in enumerate(records):
            hr = record.get('heartrate_bpm') or 0
            speed = record.get('speed_ms') or 0
            power = record.get('power_watts') or 0

            if hr > (records[max_hr_idx].get('heartrate_bpm') or 0):
                max_hr_idx = i
            if speed > (records[max_speed_idx].get('speed_ms') or 0):
                max_speed_idx = i
            if power > (records[max_power_idx].get('power_watts') or 0):
                max_power_idx = i

        # Sample at regular intervals
        for i in range(1, len(records) - 1):
            # Keep points at regular intervals
            if i % interval_points == 0:
                downsampled.append(records[i])
            # Always keep peak points
            elif i in (max_hr_idx, max_speed_idx, max_power_idx):
                if records[i] != downsampled[-1]:
                    downsampled.append(records[i])

        # Always include last point
        if records[-1] != downsampled[-1]:
            downsampled.append(records[-1])

        return downsampled

    def get_gear(self, gear_id):
        return self._request('GET', f'gear/{gear_id}')

    def get_routes(self, athlete_id, page=1, per_page=30):
        params = {'page': page, 'per_page': per_page}
        return self._request('GET', f'athletes/{athlete_id}/routes', params=params)

    def get_athlete_zones(self):
        return self._request('GET', 'athlete/zones')


def _get_safe(stream_list, index):
    """Get value from stream list at index, return None if out of bounds or None."""
    if stream_list and len(stream_list) > index:
        return stream_list[index]
    return None
