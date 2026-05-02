import json
from datetime import datetime
from models.athlete import Athlete
from models.activity import Activity, ActivityStream
from models.gear import Gear
from models.route import Route
from models.zone import AthleteZone


class ExportService:

    @staticmethod
    def export_all_data(athlete_id):
        athlete = Athlete.query.get(athlete_id)
        if not athlete:
            raise ValueError(f"Athlete {athlete_id} not found")

        export_data = {
            'export_info': {
                'exported_at': datetime.utcnow().isoformat() + 'Z',
                'athlete_id': athlete_id,
                'data_version': '1.0'
            },
            'athlete': athlete.to_dict(),
            'zones': ExportService._export_zones(athlete_id),
            'gear': [g.to_dict() for g in Gear.query.filter_by(athlete_id=athlete_id).all()],
            'activities': ExportService._export_activities(athlete_id),
            'routes': [r.to_dict() for r in Route.query.filter_by(athlete_id=athlete_id).all()],
            'statistics': ExportService._calculate_statistics(athlete_id)
        }

        return json.dumps(export_data, indent=2, default=str)

    @staticmethod
    def _export_zones(athlete_id):
        zones = AthleteZone.query.filter_by(athlete_id=athlete_id).all()
        result = {}

        for zone in zones:
            zone_data = json.loads(zone.zones_json)
            result[zone.zone_type + '_zones'] = zone_data

        return result

    @staticmethod
    def _export_activities(athlete_id):
        from sqlalchemy.orm import joinedload
        # Eager load streams to ensure they're included
        activities = Activity.query.options(joinedload(Activity.streams)).filter_by(athlete_id=athlete_id).all()
        return [a.to_dict(include_streams=True) for a in activities]

    @staticmethod
    def _calculate_statistics(athlete_id):
        activities = Activity.query.filter_by(athlete_id=athlete_id).all()

        if not activities:
            return {
                'total_activities': 0,
                'total_distance': 0,
                'total_moving_time': 0
            }

        total_distance = sum(a.distance or 0 for a in activities)
        total_moving_time = sum(a.moving_time or 0 for a in activities)

        activities_by_type = {}
        gear_usage = {}

        for a in activities:
            if a.type:
                activities_by_type[a.type] = activities_by_type.get(a.type, 0) + 1

            if a.gear_id:
                if a.gear_id not in gear_usage:
                    gear = Gear.query.get(a.gear_id)
                    gear_usage[a.gear_id] = {
                        'gear_id': a.gear_id,
                        'gear_name': gear.name if gear else a.gear_id,
                        'activity_count': 0,
                        'total_distance': 0
                    }
                gear_usage[a.gear_id]['activity_count'] += 1
                gear_usage[a.gear_id]['total_distance'] += a.distance or 0

        return {
            'total_activities': len(activities),
            'total_distance': round(total_distance, 2),
            'total_moving_time': total_moving_time,
            'first_activity_date': min(a.start_date for a in activities if a.start_date).isoformat(),
            'last_activity_date': max(a.start_date for a in activities if a.start_date).isoformat(),
            'activities_by_type': activities_by_type,
            'gear_usage': list(gear_usage.values())
        }
