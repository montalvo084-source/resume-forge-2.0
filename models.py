from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class MasterResume(db.Model):
    __tablename__ = 'master_resume'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def upsert(cls, content):
        row = cls.query.first()
        if row is None:
            row = cls(content=content)
            db.session.add(row)
        else:
            row.content = content
            row.updated_at = datetime.utcnow()
        db.session.commit()
        return row

    @classmethod
    def get(cls):
        return cls.query.first()


class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.Text, nullable=False)
    job_title = db.Column(db.Text, nullable=False)
    job_description = db.Column(db.Text)
    why_applying = db.Column(db.Text)
    tailored_resume_text = db.Column(db.Text)
    tailored_resume_html = db.Column(db.Text)
    status = db.Column(db.Text, default='applied')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    corrected_company = db.Column(db.Boolean, default=False)
    corrected_title = db.Column(db.Boolean, default=False)


class Setting(db.Model):
    __tablename__ = 'settings'
    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text)

    @classmethod
    def get(cls, key, default=None):
        row = db.session.get(cls, key)
        return row.value if row else default

    @classmethod
    def set(cls, key, value):
        row = db.session.get(cls, key)
        if row is None:
            row = cls(key=key, value=str(value))
            db.session.add(row)
        else:
            row.value = str(value)
        db.session.commit()


SETTING_DEFAULTS = {
    'goal_total': '100',
    'goal_quarter': 'Q2 2025',
    'user_name': 'Gabriel',
    'starting_count': '0',
}


def seed_settings():
    for k, v in SETTING_DEFAULTS.items():
        if db.session.get(Setting, k) is None:
            db.session.add(Setting(key=k, value=v))
    db.session.commit()
