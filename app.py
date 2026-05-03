from flask import Flask
from config import Config
from extensions import db


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.validate()
    db.init_app(app)

    # Import models so they're registered with SQLAlchemy
    from models import athlete, activity, gear, route, zone, sync_job

    # Set app on DataFetcher for background thread context
    from services.data_fetcher import DataFetcher
    DataFetcher.set_app(app)

    with app.app_context():
        db.create_all()

    from routes.web_routes import web_bp
    from routes.auth_routes import auth_bp
    from routes.export_routes import export_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(export_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
