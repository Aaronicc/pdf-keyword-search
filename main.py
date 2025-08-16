import os
from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from PyPDF2 import PdfReader

app = Flask(__name__)

# ----------------------------
# Database setup (SQLite only)
# ----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///keywords.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ----------------------------
# Models
# ----------------------------
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # "positive" or "negative"

with app.app_context():
    db.create_all()

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def index():
    keywords = Keyword.query.all()
    return render_template("index.html", keywords=keywords)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("word")
    ktype = request.form.get("type")  # positive / negative

    if not word or not ktype:
        return jsonify({"error": "Missing keyword or type"}), 400

    existing = Keyword.query.filter_by(word=word).first()
    if existing:
        return jsonify({"error": "Keyword already exists"}), 400

    new_kw = Keyword(word=word, type=ktype)
    db.session.add(new_kw)
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:kw_id>", methods=["POST"])
def delete_keyword(kw_id):
    kw = Keyword.query.get_or_404(kw_id)
    db.session.delete(kw)
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/upload_pdf", methods=["POST"])
def upload_pdf():
    file = request.files["pdf"]
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""

    found = []
    for kw in Keyword.query.all():
        if kw.word.lower() in text.lower():
            found.append({"word": kw.word, "type": kw.type})

    return jsonify({"matches": found})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
