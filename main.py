import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract

# ---------------- Flask Setup ----------------
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Use PostgreSQL if on Render, else fallback to SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///keywords.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------------- Database Model ----------------
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # "positive" or "negative"

with app.app_context():
    db.create_all()

# ---------------- Helpers ----------------
def extract_text_from_pdf(filepath):
    """Extract text from a PDF file"""
    text = ""
    try:
        reader = PdfReader(filepath)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        text = f"[Error reading PDF: {e}]"
    return text

def extract_text_from_image(filepath):
    """Extract text from an image using OCR"""
    try:
        image = Image.open(filepath)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        text = f"[Error reading Image: {e}]"
    return text

def highlight_keywords(text, keywords):
    """Highlight positive (green) and negative (red) keywords"""
    for kw in keywords:
        if kw.type == "positive":
            text = text.replace(kw.word, f"<mark style='background: lightgreen;'>{kw.word}</mark>")
        else:
            text = text.replace(kw.word, f"<mark style='background: pink;'>{kw.word}</mark>")
    return text

# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def index():
    keywords = Keyword.query.all()
    return render_template("index.html", keywords=keywords)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("keyword")
    type_ = request.form.get("type")

    if word:
        # Prevent duplicates
        existing = Keyword.query.filter_by(word=word).first()
        if not existing:
            new_kw = Keyword(word=word, type=type_)
            db.session.add(new_kw)
            db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:id>", methods=["POST"])
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/", methods=["POST"])
def upload_files():
    uploaded_files = request.files.getlist("files")
    keywords = Keyword.query.all()
    results = []

    for file in uploaded_files:
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            # Extract text depending on file type
            if filename.lower().endswith(".pdf"):
                text = extract_text_from_pdf(filepath)
            else:
                text = extract_text_from_image(filepath)

            highlighted = highlight_keywords(text, keywords)

            results.append({
                "filename": filename,
                "content": highlighted
            })

    return render_template("results.html", results=results, keywords=keywords)

# ---------------- Run ----------------
if __name__ == "__main__":
    app.run(debug=True)
