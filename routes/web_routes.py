from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from models.athlete import Athlete
from models.activity import Activity
from models.gear import Gear
from models.route import Route
from services.data_fetcher import DataFetcher
from models.sync_job import SyncJob

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    athlete_id = session.get('athlete_id')

    if not athlete_id or not current_app.config.get('STRAVA_CLIENT_ID'):
        return render_template('index.html')

    athlete = Athlete.query.get(athlete_id)
    if not athlete:
        session.clear()
        return render_template('index.html')

    stats = {
        'total_activities': Activity.query.filter_by(athlete_id=athlete_id).count(),
        'total_distance': sum(a.distance or 0 for a in Activity.query.filter_by(athlete_id=athlete_id).all())
    }

    return render_template('dashboard.html',
                          athlete=athlete,
                          stats=stats,
                          gear_count=Gear.query.filter_by(athlete_id=athlete_id).count(),
                          routes_count=Route.query.filter_by(athlete_id=athlete_id).count())


@web_bp.route('/config', methods=['POST'])
def save_config():
    data = request.get_json()
    client_id = data.get('client_id')
    client_secret = data.get('client_secret')

    if not client_id or not client_secret:
        return jsonify({'error': 'Client ID and Secret are required'}), 400

    current_app.config['STRAVA_CLIENT_ID'] = client_id
    current_app.config['STRAVA_CLIENT_SECRET'] = client_secret

    from api.oauth import StravaOAuth
    auth_url = StravaOAuth.get_authorization_url()

    return jsonify({'redirect_url': auth_url})


@web_bp.route('/sync/start', methods=['POST'])
def start_sync():
    athlete_id = session.get('athlete_id')
    if not athlete_id:
        return jsonify({'error': 'Not authenticated'}), 401

    job_id = DataFetcher.start_sync(athlete_id)
    return jsonify({'job_id': job_id})


@web_bp.route('/sync/status')
def sync_status():
    athlete_id = session.get('athlete_id')
    if not athlete_id:
        return jsonify({'error': 'Not authenticated'}), 401

    job = SyncJob.query.filter_by(athlete_id=athlete_id).order_by(SyncJob.id.desc()).first()

    if job:
        return jsonify({
            'status': job.status,
            'progress': job.progress,
            'current_step': job.current_step,
            'error': job.error_message
        })

    return jsonify({'status': 'idle'})


@web_bp.route('/debug')
def debug():
    athlete_id = session.get('athlete_id')
    if not athlete_id:
        return jsonify({'error': 'Not authenticated'}), 401

    activities = Activity.query.filter_by(athlete_id=athlete_id).all()
    return jsonify({
        'athlete_id': athlete_id,
        'activity_count': len(activities),
        'activities': [{'id': a.id, 'name': a.name, 'distance': a.distance, 'moving_time': a.moving_time} for a in activities[:5]]
    })
