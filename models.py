from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    positive = db.Column(db.Boolean, default=True)
