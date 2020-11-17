import datetime

from app import db

class Configuration(db.Model):
    __tablename__ = 'configuration'
    id = db.Column(db.Integer, primary_key=True)
    grow_threshold = db.Column(db.Float)
    shrink_threshold = db.Column(db.Float)
    expand_ratio = db.Column(db.Float)
    shrink_ratio = db.Column(db.Float)
    create_time = db.Column(db.DateTime)

    def __repr__(self):
        return '<Configuration {}>'.format(self.id)
        

class HttpRequestCount(db.Model):
    __tablename__ = 'http_request_count'
    id = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow) 
    
    def __repr__(self):
        return "<HttpRequestCount %r>" % self.id