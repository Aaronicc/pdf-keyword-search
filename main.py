import os
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF for PDF text
import pytesseract
from PIL import Image

app = Flask(__name__)
app.secret_key = "supersecret"

# Database setup (SQLite or PostgreSQL if DATABASE_URL exists)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///keywords.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Keyword model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # positive or negative

with app.app_context():
    db.create_all()

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def extract_text_from_pdf(pdf_path):
    """Extracts text from PDF using PyMuPDF."""
    text_by_page = []
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        text_by_page.append((page_num, text))
    return text_by_page


def extract_text_from_image(image_path):
    """Extracts text from an image using Tesseract OCR."""
    image = Image.open(image_path)
    text = pytesseract.image_to_string(image)
    return text


def search_keywords(text_by_page, keywords):
    """Search for keywords inside extracted text by page."""
    matches = []
    counts = {"positive": 0, "negative": 0}

    for page_num, text in text_by_page:
        for kw in keywords:
            if kw.word.lower() in text.lower():
                snippet_start = text.lower().find(kw.word.lower())
                snippet = text[snippet_start:snippet_start + 100]
                matches.append({
                    "keyword": kw.word,
                    "type": kw.type,
                    "page": page_num,
                    "snippet": snippet + "..."
                })
                counts[kw.type] += 1
    return matches, counts


@app.route("/")
def index():
    keywords = Keyword.query.all()
    return render_template("index.html", keywords=keywords)


@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("word")
    ktype = request.form.get("type")
    if not word or not ktype:
        flash("Keyword and type are required!")
        return redirect(url_for("index"))

    if Keyword.query.filter_by(word=word).first():
        flash("Keyword already exists!")
        return redirect(url_for("index"))

    new_kw = Keyword(word=word, type=ktype)
    db.session.add(new_kw)
    db.session.commit()
    flash(f"Added keyword: {word} ({ktype})")
    return redirect(url_for("index"))


@app.route("/delete_keyword/<int:kw_id>")
def delete_keyword(kw_id):
    kw = Keyword.query.get_or_404(kw_id)
    db.session.delete(kw)
    db.session.commit()
    flash(f"Deleted keyword: {kw.word}")
    return redirect(url_for("index"))


@app.route("/upload", methods=["POST"])
def upload_file():
    if "files" not in request.files:
        flash("No file uploaded")
        return redirect(url_for("index"))

    files = request.files.getlist("files")
    keywords = Keyword.query.all()
    all_matches = []
    total_counts = {"positive": 0, "negative": 0}

    for file in files:
        if file.filename == "":
            continue
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        if filename.lower().endswith(".pdf"):
            text_by_page = extract_text_from_pdf(filepath)
        else:
            text = extract_text_from_image(filepath)
            text_by_page = [(1, text)]  # OCR result as page 1

        matches, counts = search_keywords(text_by_page, keywords)
        all_matches.extend(matches)
        total_counts["positive"] += counts["positive"]
        total_counts["negative"] += counts["negative"]

    return render_template("results.html", matches=all_matches, counts=total_counts)


if __name__ == "__main__":
    app.run(debug=True)
