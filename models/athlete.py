from datetime import datetime
from extensions import db
import json


class Athlete(db.Model):
    __tablename__ = 'athletes'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    firstname = db.Column(db.String(100))
    lastname = db.Column(db.String(100))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    sex = db.Column(db.String(10))
    premium = db.Column(db.Boolean, default=False)
    summit = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    follower_count = db.Column(db.Integer)
    friend_count = db.Column(db.Integer)
    measurement_preference = db.Column(db.String(20))
    ftp = db.Column(db.Integer)
    weight = db.Column(db.Float)
    profile_medium = db.Column(db.String(500))
    profile = db.Column(db.String(500))

    access_token = db.Column(db.String(500))
    refresh_token = db.Column(db.String(500))
    token_expires_at = db.Column(db.Integer)
    scopes = db.Column(db.String(200))

    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data_json = db.Column(db.Text)

    activities = db.relationship('Activity', backref='athlete', lazy=True, cascade='all, delete-orphan')
    gear_items = db.relationship('Gear', backref='athlete', lazy=True, cascade='all, delete-orphan')
    routes = db.relationship('Route', backref='athlete', lazy=True, cascade='all, delete-orphan')
    zones = db.relationship('AthleteZone', backref='athlete', lazy=True, cascade='all, delete-orphan')
    sync_jobs = db.relationship('SyncJob', backref='athlete', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def create_or_update_from_api(data, token_data):
        athlete = Athlete.query.filter_by(id=data['id']).first()
        if not athlete:
            athlete = Athlete(id=data['id'])

        athlete.username = data.get('username')
        athlete.firstname = data.get('firstname')
        athlete.lastname = data.get('lastname')
        athlete.city = data.get('city')
        athlete.state = data.get('state')
        athlete.country = data.get('country')
        athlete.sex = data.get('sex')
        athlete.premium = data.get('premium', False)
        athlete.summit = data.get('summit', False)
        athlete.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None
        athlete.follower_count = data.get('follower_count')
        athlete.friend_count = data.get('friend_count')
        athlete.measurement_preference = data.get('measurement_preference')
        athlete.ftp = data.get('ftp')
        athlete.weight = data.get('weight')
        athlete.profile_medium = data.get('profile_medium')
        athlete.profile = data.get('profile')

        athlete.access_token = token_data['access_token']
        athlete.refresh_token = token_data['refresh_token']
        athlete.token_expires_at = token_data['expires_at']
        athlete.scopes = token_data.get('scopes', '')
        athlete.synced_at = datetime.utcnow()
        athlete.raw_data_json = json.dumps(data)

        db.session.add(athlete)
        db.session.commit()
        return athlete

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'sex': self.sex,
            'premium': self.premium,
            'summit': self.summit,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'follower_count': self.follower_count,
            'friend_count': self.friend_count,
            'measurement_preference': self.measurement_preference,
            'ftp': self.ftp,
            'weight': self.weight,
            'profile': self.profile
        }
