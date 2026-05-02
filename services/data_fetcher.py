import threading
import json
import traceback
from datetime import datetime, timedelta
from models.athlete import Athlete
from models.activity import Activity, ActivityStream
from models.gear import Gear
from models.zone import AthleteZone
from models.sync_job import SyncJob
from api.strava_client import StravaClient
from extensions import db


class DataFetcher:
    _active_jobs = {}
    _app = None

    @classmethod
    def set_app(cls, app):
        cls._app = app

    @classmethod
    def start_sync(cls, athlete_id):
        if athlete_id in cls._active_jobs:
            job = SyncJob.query.filter_by(athlete_id=athlete_id, status='running').first()
            if job:
                return job.id

        job = SyncJob(athlete_id=athlete_id, status='running', progress=0, current_step='Initializing...')
        db.session.add(job)
        db.session.commit()

        thread = threading.Thread(target=cls._fetch_all_data, args=(job.id, athlete_id))
        thread.daemon = True
        thread.start()

        cls._active_jobs[athlete_id] = thread
        return job.id

    @classmethod
    def _get_session(cls):
        return db.session

    @classmethod
    def _fetch_all_data(cls, job_id, athlete_id):
        job = None
        try:
            with cls._app.app_context():
                session = cls._get_session()
                job = session.query(SyncJob).get(job_id)

                job.update_progress(5, 'Connecting to Strava...')
                client = StravaClient(athlete_id)

                job.update_progress(10, 'Fetching athlete profile...')
                athlete_data = client.get_athlete()
                athlete = session.query(Athlete).get(athlete_id)

                job.update_progress(15, 'Fetching athlete zones...')
                cls._fetch_athlete_zones(client, athlete_id, session)

                job.update_progress(20, 'Fetching activities from the last year...')
                one_year_ago = int((datetime.utcnow() - timedelta(days=365)).timestamp())
                print(f"[*] Fetching activities since {datetime.utcnow() - timedelta(days=365)}")
                activity_count = cls._fetch_activities_optimized(client, athlete_id, job, session, after=one_year_ago)
                job.total_items = activity_count

                job.update_progress(90, 'Fetching gear...')
                cls._fetch_gear(client, athlete, athlete_data, session)

                job.update_progress(100, f'Complete! Fetched {activity_count} activities.')
                job.complete()

        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            print(f"Sync error: {error_msg}")
            if job:
                with cls._app.app_context():
                    job_session = cls._get_session()
                    job_obj = job_session.query(SyncJob).get(job_id)
                    if job_obj:
                        job_obj.fail(error_msg[:1000])
        finally:
            if athlete_id in cls._active_jobs:
                del cls._active_jobs[athlete_id]

    @classmethod
    def _fetch_athlete_zones(cls, client, athlete_id, session):
        try:
            zones_data = client.get_athlete_zones()
            for zone_type in ['heart_rate', 'power']:
                zone_key = f'{zone_type}_zones'
                if zone_key in zones_data:
                    zones = zones_data[zone_key]
                    if zones:
                        session.query(AthleteZone).filter_by(athlete_id=athlete_id, zone_type=zone_type).delete()
                        for zone in zones:
                            zone_obj = AthleteZone(
                                athlete_id=athlete_id,
                                zone_type=zone_type,
                                zones_json=json.dumps(zone)
                            )
                            session.add(zone_obj)
            session.commit()
        except Exception as e:
            print(f"[!] Zones error: {e}")

    @classmethod
    def _fetch_activities_optimized(cls, client, athlete_id, job, session, after=None):
        """
        Fetch activities with robust error handling.
        Continues even if individual activities fail.
        """
        page = 1
        per_page = 200
        total_count = 0
        failed_count = 0

        print(f"[*] Fetching activities...")

        while True:
            try:
                activities = client.get_activities(page=page, per_page=per_page, after=after)

                if not activities:
                    print(f"[*] No more activities found")
                    break

                print(f"[*] Page {page}: {len(activities)} activities")

                for activity_data in activities:
                    try:
                        cls._save_activity_training_data(activity_data, athlete_id, session, client)
                        total_count += 1

                        progress = 20 + min(int((total_count * 70) / 200), 70)
                        job.update_progress(progress, f'{total_count} activities...')
                    except Exception as e:
                        failed_count += 1
                        print(f"  ! Failed to save activity {activity_data.get('id')}: {e}")
                        # Continue with next activity
                        continue

                if len(activities) < per_page:
                    break

                page += 1

            except Exception as e:
                print(f"[!] Page {page} error: {e}")
                traceback.print_exc()
                break

        print(f"[*] Complete: {total_count} activities saved, {failed_count} failed")
        return total_count

    @classmethod
    def _save_activity_training_data(cls, activity_data, athlete_id, session, client):
        """
        Save training-relevant data with smart-sampled streams.
        Uses 20-second intervals to keep data manageable.
        """
        activity_id = activity_data['id']

        activity = session.query(Activity).filter_by(id=activity_id).first()
        if not activity:
            activity = Activity(id=activity_id, athlete_id=athlete_id)
            session.add(activity)

        # ===== TRAINING DATA ONLY =====
        activity.name = activity_data.get('name')
        activity.distance = activity_data.get('distance')
        activity.moving_time = activity_data.get('moving_time')
        activity.elapsed_time = activity_data.get('elapsed_time')
        activity.total_elevation_gain = activity_data.get('total_elevation_gain')
        activity.elev_high = activity_data.get('elev_high')
        activity.elev_low = activity_data.get('elev_low')
        activity.type = activity_data.get('type')
        activity.sport_type = activity_data.get('sport_type')

        if activity_data.get('start_date'):
            activity.start_date = datetime.fromisoformat(activity_data['start_date'].replace('Z', '+00:00'))
        if activity_data.get('start_date_local'):
            activity.start_date_local = datetime.fromisoformat(activity_data['start_date_local'].replace('Z', '+00:00'))

        activity.timezone = activity_data.get('timezone')
        activity.trainer = activity_data.get('trainer', False)

        # Performance metrics
        activity.average_speed = activity_data.get('average_speed')
        activity.max_speed = activity_data.get('max_speed')
        activity.average_cadence = activity_data.get('average_cadence')
        activity.average_watts = activity_data.get('average_watts')
        activity.weighted_average_watts = activity_data.get('weighted_average_watts')
        activity.kilojoules = activity_data.get('kilojoules')
        activity.device_watts = activity_data.get('device_watts', False)
        activity.max_watts = activity_data.get('max_watts')
        activity.has_heartrate = activity_data.get('has_heartrate', False)
        activity.average_heartrate = activity_data.get('average_heartrate')
        activity.max_heartrate = activity_data.get('max_heartrate')
        activity.suffer_score = activity_data.get('suffer_score')
        activity.calories = activity_data.get('calories')
        activity.gear_id = activity_data.get('gear_id')
        activity.workout_type = activity_data.get('workout_type')

        activity.synced_at = datetime.utcnow()

        session.flush()

        # Always fetch streams - they contain speed, distance, altitude, etc.
        # even if no HR/power data is present
        cls._fetch_streams_downsampled(client, activity_id, session)

        session.commit()

    @classmethod
    def _fetch_streams_downsampled(cls, client, activity_id, session):
        """
        Fetch streams and downsample to 20-second intervals.
        This keeps data manageable while preserving enough detail for analysis.
        """
        try:
            session.query(ActivityStream).filter_by(activity_id=activity_id).delete()

            # Fetch raw streams data
            records = client.get_activity_streams(activity_id)

            if records and len(records) > 0:
                print(f"    Original: {len(records)} data points")

                # Downsample to ~20-second intervals
                downsampled = client.downsample_records(records, interval_seconds=20)

                print(f"    Downsampled: {len(downsampled)} points")

                # Save to database
                stream_obj = ActivityStream(
                    activity_id=activity_id,
                    stream_type='records',
                    data_json=json.dumps(downsampled)
                )
                session.add(stream_obj)
                session.flush()
                print(f"    ✓ Streams saved")
            else:
                print(f"    ! No stream data returned from Strava")
        except Exception as e:
            print(f"    ! Stream fetch error: {e}")
            traceback.print_exc()

    @classmethod
    def _fetch_gear(cls, client, athlete, athlete_data, session):
        if not athlete:
            return

        shoes = athlete_data.get('shoes', [])
        bikes = athlete_data.get('bikes', [])

        for gear_data in shoes + bikes:
            gear_id = gear_data.get('id')
            if gear_id:
                gear = session.query(Gear).filter_by(id=gear_id).first()
                if not gear:
                    gear = Gear(id=gear_id, athlete_id=athlete.id)
                    session.add(gear)

                gear.name = gear_data.get('name')
                gear.distance = gear_data.get('distance')
                gear.primary_gear = gear_data.get('primary', False)
                gear.frame_type = gear_data.get('frame_type')
                gear.brand_name = gear_data.get('brand_name')
                gear.model_name = gear_data.get('model_name')
                gear.synced_at = datetime.utcnow()

        session.commit()
