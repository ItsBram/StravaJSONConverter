from datetime import datetime
from extensions import db
import json


class Route(db.Model):
    __tablename__ = 'routes'

    id = db.Column(db.Integer, primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athletes.id'), nullable=False)
    name = db.Column(db.String(200))
    description = db.Column(db.Text)
    distance = db.Column(db.Float)
    elevation_gain = db.Column(db.Float)
    type = db.Column(db.Integer)
    sub_type = db.Column(db.Integer)
    private = db.Column(db.Boolean, default=False)
    starred = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    estimated_moving_time = db.Column(db.Integer)

    map_polyline = db.Column(db.Text)
    map_summary_polyline = db.Column(db.Text)

    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data_json = db.Column(db.Text)

    segments = db.relationship('RouteSegment', backref='route', lazy=True, cascade='all, delete-orphan')

    @staticmethod
    def create_or_update_from_api(athlete_id, data):
        route = Route.query.filter_by(id=data['id']).first()
        if not route:
            route = Route(id=data['id'], athlete_id=athlete_id)

        route.name = data.get('name')
        route.description = data.get('description')
        route.distance = data.get('distance')
        route.elevation_gain = data.get('elevation_gain')
        route.type = data.get('type')
        route.sub_type = data.get('sub_type')
        route.private = data.get('private', False)
        route.starred = data.get('starred', False)

        if data.get('created_at'):
            route.created_at = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if data.get('updated_at'):
            route.updated_at = datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00'))

        route.estimated_moving_time = data.get('estimated_moving_time')

        map_data = data.get('map', {})
        route.map_polyline = map_data.get('polyline') if map_data else None
        route.map_summary_polyline = map_data.get('summary_polyline') if map_data else None

        route.synced_at = datetime.utcnow()
        route.raw_data_json = json.dumps(data)

        db.session.add(route)
        db.session.commit()
        return route

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'distance': self.distance,
            'elevation_gain': self.elevation_gain,
            'type': self.type,
            'private': self.private,
            'starred': self.starred,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'estimated_moving_time': self.estimated_moving_time
        }


class RouteSegment(db.Model):
    __tablename__ = 'route_segments'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    route_id = db.Column(db.Integer, db.ForeignKey('routes.id'), nullable=False)
    segment_id = db.Column(db.Integer)
    name = db.Column(db.String(200))
    distance = db.Column(db.Float)
    average_grade = db.Column(db.Float)
    maximum_grade = db.Column(db.Float)
    elevation_high = db.Column(db.Float)
    elevation_low = db.Column(db.Float)
    climb_category = db.Column(db.Integer)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
