from datetime import datetime
from extensions import db
import json


class Activity(db.Model):
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athletes.id'), nullable=False, index=True)
    external_id = db.Column(db.String(100))
    upload_id = db.Column(db.Integer)
    name = db.Column(db.String(200))
    distance = db.Column(db.Float)
    moving_time = db.Column(db.Integer)
    elapsed_time = db.Column(db.Integer)
    total_elevation_gain = db.Column(db.Float)
    elev_high = db.Column(db.Float)
    elev_low = db.Column(db.Float)
    type = db.Column(db.String(50))
    sport_type = db.Column(db.String(50))
    start_date = db.Column(db.DateTime, index=True)
    start_date_local = db.Column(db.DateTime)
    timezone = db.Column(db.String(50))
    achievement_count = db.Column(db.Integer)
    kudos_count = db.Column(db.Integer)
    comment_count = db.Column(db.Integer)
    athlete_count = db.Column(db.Integer)
    photo_count = db.Column(db.Integer)
    trainer = db.Column(db.Boolean, default=False)
    commute = db.Column(db.Boolean, default=False)
    manual = db.Column(db.Boolean, default=False)
    private = db.Column(db.Boolean, default=False)
    flagged = db.Column(db.Boolean, default=False)
    workout_type = db.Column(db.Integer)

    average_speed = db.Column(db.Float)
    max_speed = db.Column(db.Float)
    average_cadence = db.Column(db.Float)
    average_watts = db.Column(db.Float)
    weighted_average_watts = db.Column(db.Float)
    kilojoules = db.Column(db.Float)
    device_watts = db.Column(db.Boolean, default=False)
    max_watts = db.Column(db.Integer)
    has_heartrate = db.Column(db.Boolean, default=False)
    average_heartrate = db.Column(db.Float)
    max_heartrate = db.Column(db.Integer)
    suffer_score = db.Column(db.Integer)
    description = db.Column(db.Text)
    calories = db.Column(db.Float)
    gear_id = db.Column(db.String(50))

    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data_json = db.Column(db.Text)

    streams = db.relationship('ActivityStream', backref='activity', lazy=True, cascade='all, delete-orphan')
    zones = db.relationship('ActivityZone', backref='activity', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def create_or_update_from_api(athlete_id, data):
        activity = Activity.query.filter_by(id=data['id']).first()
        if not activity:
            activity = Activity(id=data['id'], athlete_id=athlete_id)

        activity.external_id = data.get('external_id')
        activity.upload_id = data.get('upload_id')
        activity.name = data.get('name')
        activity.distance = data.get('distance')
        activity.moving_time = data.get('moving_time')
        activity.elapsed_time = data.get('elapsed_time')
        activity.total_elevation_gain = data.get('total_elevation_gain')
        activity.elev_high = data.get('elev_high')
        activity.elev_low = data.get('elev_low')
        activity.type = data.get('type')
        activity.sport_type = data.get('sport_type')

        if data.get('start_date'):
            activity.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
        if data.get('start_date_local'):
            activity.start_date_local = datetime.fromisoformat(data['start_date_local'].replace('Z', '+00:00'))

        activity.timezone = data.get('timezone')
        activity.achievement_count = data.get('achievement_count')
        activity.kudos_count = data.get('kudos_count')
        activity.comment_count = data.get('comment_count')
        activity.athlete_count = data.get('athlete_count')
        activity.photo_count = data.get('photo_count')
        activity.trainer = data.get('trainer', False)
        activity.commute = data.get('commute', False)
        activity.manual = data.get('manual', False)
        activity.private = data.get('private', False)
        activity.flagged = data.get('flagged', False)
        activity.workout_type = data.get('workout_type')

        activity.average_speed = data.get('average_speed')
        activity.max_speed = data.get('max_speed')
        activity.average_cadence = data.get('average_cadence')
        activity.average_watts = data.get('average_watts')
        activity.weighted_average_watts = data.get('weighted_average_watts')
        activity.kilojoules = data.get('kilojoules')
        activity.device_watts = data.get('device_watts', False)
        activity.max_watts = data.get('max_watts')
        activity.has_heartrate = data.get('has_heartrate', False)
        activity.average_heartrate = data.get('average_heartrate')
        activity.max_heartrate = data.get('max_heartrate')
        activity.suffer_score = data.get('suffer_score')
        activity.description = data.get('description')
        activity.calories = data.get('calories')
        activity.gear_id = data.get('gear_id')
        activity.synced_at = datetime.utcnow()
        activity.raw_data_json = json.dumps(data)

        db.session.add(activity)
        db.session.commit()
        return activity

    def to_dict(self, include_streams=False):
        """Export only training-relevant data"""
        data = {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'distance': self.distance,
            'moving_time': self.moving_time,
            'elapsed_time': self.elapsed_time,
            'total_elevation_gain': self.total_elevation_gain,
            'elev_high': self.elev_high,
            'elev_low': self.elev_low,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'start_date_local': self.start_date_local.isoformat() if self.start_date_local else None,
            'timezone': self.timezone,
            'trainer': self.trainer,
            'average_speed': self.average_speed,
            'max_speed': self.max_speed,
            'average_cadence': self.average_cadence,
            'average_watts': self.average_watts,
            'weighted_average_watts': self.weighted_average_watts,
            'kilojoules': self.kilojoules,
            'max_watts': self.max_watts,
            'has_heartrate': self.has_heartrate,
            'average_heartrate': self.average_heartrate,
            'max_heartrate': self.max_heartrate,
            'suffer_score': self.suffer_score,
            'calories': self.calories,
            'gear_id': self.gear_id,
            'workout_type': self.workout_type
        }

        if include_streams:
            # Find the 'records' stream which contains all time-indexed data
            for s in self.streams:
                if s.stream_type == 'records':
                    data['records'] = json.loads(s.data_json)
                    break
            else:
                data['records'] = []

        return data


class ActivityStream(db.Model):
    __tablename__ = 'activity_streams'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False, index=True)
    stream_type = db.Column(db.String(50), nullable=False)
    data_json = db.Column(db.Text, nullable=False)
    resolution = db.Column(db.String(20))
    original_size = db.Column(db.Integer)

    __table_args__ = (db.UniqueConstraint('activity_id', 'stream_type', name='unique_activity_stream'),)


class ActivityZone(db.Model):
    __tablename__ = 'activity_zones'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activities.id'), nullable=False)
    zone_type = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer)
    sensor_based = db.Column(db.Boolean, default=False)
    custom_zones = db.Column(db.Boolean, default=False)
    max = db.Column(db.Integer)
    points = db.Column(db.Integer)
    distribution_buckets_json = db.Column(db.Text)

    def to_dict(self):
        return {
            'type': self.zone_type,
            'score': self.score,
            'sensor_based': self.sensor_based,
            'max': self.max,
            'distribution_buckets': json.loads(self.distribution_buckets_json) if self.distribution_buckets_json else []
        }
