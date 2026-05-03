from flask import Blueprint, session, send_file, Response, jsonify
from services.export_service import ExportService
from models.athlete import Athlete
from io import StringIO
import json

export_bp = Blueprint('export', __name__)


@export_bp.route('/export/all')
def export_all():
    athlete_id = session.get('athlete_id')
    if not athlete_id:
        return jsonify({'error': 'Not authenticated'}), 401

    athlete = Athlete.query.get(athlete_id)
    if not athlete:
        return jsonify({'error': 'Athlete not found'}), 404

    try:
        json_data = ExportService.export_all_data(athlete_id)

        return Response(
            json_data,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename=strava_data_{athlete_id}.json'
            }
        )
    except Exception as e:
        return jsonify({'error': 'An internal error occurred during export.'}), 500
