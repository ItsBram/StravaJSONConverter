import requests
import secrets
from flask import current_app, session, redirect, url_for
from urllib.parse import urlencode


class StravaOAuth:
    AUTH_URL = "https://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"

    @classmethod
    def generate_state(cls):
        return secrets.token_urlsafe(16)

    @classmethod
    def get_authorization_url(cls, state=None):
        if state is None:
            state = cls.generate_state()
        session['oauth_state'] = state

        params = {
            'client_id': current_app.config['STRAVA_CLIENT_ID'],
            'redirect_uri': current_app.config['STRAVA_REDIRECT_URI'],
            'response_type': 'code',
            'approval_prompt': 'auto',
            'scope': ','.join(current_app.config['STRAVA_SCOPES']),
            'state': state
        }

        return f"{cls.AUTH_URL}?{urlencode(params)}"

    @classmethod
    def exchange_code_for_token(cls, code):
        response = requests.post(cls.TOKEN_URL, data={
            'client_id': current_app.config['STRAVA_CLIENT_ID'],
            'client_secret': current_app.config['STRAVA_CLIENT_SECRET'],
            'code': code,
            'grant_type': 'authorization_code'
        })

        response.raise_for_status()
        return response.json()

    @classmethod
    def refresh_access_token(cls, refresh_token):
        response = requests.post(cls.TOKEN_URL, data={
            'client_id': current_app.config['STRAVA_CLIENT_ID'],
            'client_secret': current_app.config['STRAVA_CLIENT_SECRET'],
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        })

        response.raise_for_status()
        return response.json()

    @classmethod
    def deauthorize(cls, access_token):
        response = requests.post('https://www.strava.com/oauth/deauthorize', headers={
            'Authorization': f'Bearer {access_token}'
        })
        return response.status_code == 204
