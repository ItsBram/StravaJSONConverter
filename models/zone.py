from datetime import datetime
from extensions import db
import json


class AthleteZone(db.Model):
    __tablename__ = 'athlete_zones'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athletes.id'), nullable=False)
    zone_type = db.Column(db.String(50), nullable=False)
    zones_json = db.Column(db.Text, nullable=False)

    synced_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def create_or_update_from_api(athlete_id, zone_type, zones_data):
        existing = AthleteZone.query.filter_by(athlete_id=athlete_id, zone_type=zone_type).first()
        if existing:
            existing.zones_json = json.dumps(zones_data)
            existing.synced_at = datetime.utcnow()
            db.session.add(existing)
            db.session.commit()
            return existing

        zone = AthleteZone(athlete_id=athlete_id, zone_type=zone_type, zones_json=json.dumps(zones_data))
        db.session.add(zone)
        db.session.commit()
        return zone

    def to_dict(self):
        return {self.zone_type: json.loads(self.zones_json)}
