from datetime import datetime
from extensions import db


class SyncJob(db.Model):
    __tablename__ = 'sync_jobs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    athlete_id = db.Column(db.Integer, db.ForeignKey('athletes.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    progress = db.Column(db.Integer, default=0)
    total_items = db.Column(db.Integer)
    current_step = db.Column(db.String(200))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

    def update_progress(self, progress, step):
        self.progress = progress
        self.current_step = step
        db.session.commit()

    def complete(self):
        self.status = 'completed'
        self.progress = 100
        self.completed_at = datetime.utcnow()
        db.session.commit()

    def fail(self, error_message):
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        db.session.commit()
