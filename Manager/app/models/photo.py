import datetime

from app import db
from sqlalchemy import Column
from sqlalchemy import SmallInteger, Integer, String
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey


class Photo(db.Model):
    __tablename__ = 'photos'
    id = Column(Integer, primary_key=True, autoincrement=True)
    photo_name = Column(String(512), unique=True)
    output_name = Column(String(512), unique=True)
    nfaces = Column(Integer)
    nmasks = Column(Integer)

    # flag == 3 no faces
    # flag == 2 some with and some without masks
    # flag == 1 all with masks
    # flag == 0 none with masks
    photo_type = Column(Integer)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(String(255), ForeignKey('md_user.id'))

    def __repr__(self):
        return "<Photo %r>" % self.id
