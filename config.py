import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
    STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
    STRAVA_REDIRECT_URI = os.getenv('STRAVA_REDIRECT_URI', 'http://localhost:5000/auth/callback')
    STRAVA_SCOPES = ['read', 'read_all', 'profile:read_all', 'activity:read_all']
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'strava_data.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @classmethod
    def validate(cls):
        missing = []
        if not cls.STRAVA_CLIENT_ID:
            missing.append('STRAVA_CLIENT_ID')
        if not cls.STRAVA_CLIENT_SECRET:
            missing.append('STRAVA_CLIENT_SECRET')
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}. "
                f"Set these in your .env file or server environment."
            )
