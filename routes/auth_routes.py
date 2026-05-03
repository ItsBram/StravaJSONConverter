from flask import Blueprint, request, session, redirect, url_for, current_app, jsonify
from api.oauth import StravaOAuth
from models.athlete import Athlete
from models.activity import Activity
from models.gear import Gear
from models.route import Route
from models.zone import AthleteZone
from extensions import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/auth/strava')
def auth_strava():
    if not current_app.config.get('STRAVA_CLIENT_ID') or not current_app.config.get('STRAVA_CLIENT_SECRET'):
        return "Server configuration error: Strava API credentials are not configured. Please contact the administrator.", 500

    auth_url = StravaOAuth.get_authorization_url()
    return redirect(auth_url)


@auth_bp.route('/auth/callback')
def auth_callback():
    error = request.args.get('error')
    if error:
        return f"Authorization failed: {error}", 400

    code = request.args.get('code')
    state = request.args.get('state')

    saved_state = session.get('oauth_state')
    if saved_state and state != saved_state:
        return "Invalid state parameter", 400

    try:
        token_data = StravaOAuth.exchange_code_for_token(code)

        import requests
        athlete_response = requests.get(
            'https://www.strava.com/api/v3/athlete',
            headers={'Authorization': f"Bearer {token_data['access_token']}"}
        )
        athlete_response.raise_for_status()
        athlete_data = athlete_response.json()

        athlete = Athlete.create_or_update_from_api(athlete_data, token_data)

        session['athlete_id'] = athlete.id
        session.pop('oauth_state', None)

        # Auto-start data fetch on first connection
        from services.data_fetcher import DataFetcher
        DataFetcher.start_sync(athlete.id)

        return redirect(url_for('web.index'))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return "An internal error occurred during authorization.", 500


@auth_bp.route('/auth/logout', methods=['POST'])
def logout():
    athlete_id = session.get('athlete_id')

    if athlete_id:
        athlete = Athlete.query.get(athlete_id)
        if athlete and athlete.access_token:
            try:
                StravaOAuth.deauthorize(athlete.access_token)
            except Exception as e:
                print(f"Deauthorization error: {e}")

    session.clear()
    return redirect(url_for('web.index'))
