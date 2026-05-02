from datetime import datetime
from extensions import db
import json


class Gear(db.Model):
    __tablename__ = 'gear'

    id = db.Column(db.String(50), primary_key=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athletes.id'), nullable=False)
    name = db.Column(db.String(200))
    brand_name = db.Column(db.String(100))
    model_name = db.Column(db.String(100))
    primary_gear = db.Column(db.Boolean, default=False)
    distance = db.Column(db.Float)
    frame_type = db.Column(db.Integer)
    description = db.Column(db.Text)

    synced_at = db.Column(db.DateTime, default=datetime.utcnow)
    raw_data_json = db.Column(db.Text)

    @staticmethod
    def create_or_update_from_api(athlete_id, data):
        gear = Gear.query.filter_by(id=data['id']).first()
        if not gear:
            gear = Gear(id=data['id'], athlete_id=athlete_id)

        gear.name = data.get('name')
        gear.brand_name = data.get('brand_name')
        gear.model_name = data.get('model_name')
        gear.primary_gear = data.get('primary', False)
        gear.distance = data.get('distance')
        gear.frame_type = data.get('frame_type')
        gear.description = data.get('description')
        gear.synced_at = datetime.utcnow()
        gear.raw_data_json = json.dumps(data)

        db.session.add(gear)
        db.session.commit()
        return gear

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'brand_name': self.brand_name,
            'model_name': self.model_name,
            'primary': self.primary_gear,
            'distance': self.distance,
            'frame_type': self.frame_type,
            'description': self.description
        }
