import datetime

from flask import current_app
from app import db

from sqlalchemy import Column
from sqlalchemy import SmallInteger, Integer, String
from sqlalchemy import DateTime

from werkzeug.security import check_password_hash, generate_password_hash
from time import time
import jwt


class User(db.Model):
    __tablename__ = 'md_user'
    ROLE_ADMIN = 1
    ROLE_USER = 0

    id = Column(String(255), primary_key=True)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255))
    password = Column(db.String(255))

    role = Column(SmallInteger, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.Integer, nullable=False, default=1)

    photos = db.relationship('Photo', backref='User', lazy='dynamic')

    def __init__(self, id, username, email, password, role, status):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.role = role
        self.status = status

    def check_password(self, raw):
        if not self.password:
            return False
        return check_password_hash(self.password, raw)

    def update_password(self, new_password):
        self.password = generate_password_hash(new_password)

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256'
        ).decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'], algorithm=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.status

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<User %r>' % self.username



