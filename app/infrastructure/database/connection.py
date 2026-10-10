import datetime as dt

from flask_sqlalchemy import SQLAlchemy

from app.domain.time import utcnow

db = SQLAlchemy()

__all__ = ["db", "utcnow"]