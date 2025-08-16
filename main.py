import os
import re
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract

# ---------------- Flask Setup ----------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- Database Setup ----------------
uri = os.getenv("DATABASE_URL", "sqlite:///keywords.db")
# Render may give postgres:// — SQLAlchemy expects postgresql://
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---------------- Model ----------------
class Keyword(db.Model):
    id = Column(Integer, primary_key=True)
    word = Column(String(100), unique=True, nullable=False)
    type = Column(String(20), nullable=False)  # "positive" or "negative"

with app.app_context():
    db.create_all()

# ---------------- Helpers ----------------
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}

def allowed_file(filename: str) -> bool:
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS

def extract_text_from_pdf(filepath):
    """Extract text per page from a PDF file; returns list[(page_num, text)]."""
    pages = []
    with open(filepath, "rb") as f:
        reader = PdfReader(f)
        for i, page in enumerate(reader.pages, start=1):
            txt = page.extract_text() or ""
            pages.append((i, txt))
    return pages

def extract_text_from_image(filepath):
    """OCR text from an image; returns list with single 'page'."""
    image = Image.open(filepath)
    text = pytesseract.image_to_string(image)
    return [(1, text)]

def highlight_snippet(snippet, word):
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)

def search_keywords(text_pages, keywords):
    """
    Search each keyword with a small context window.
    Returns list of dicts: {word, type, page, snippet}
    """
    matches = []
    for page_num, text in text_pages:
        lower_text = text.lower()
        for kw in keywords:
            w = kw.word
            idx = 0
            while True:
                pos = lower_text.find(w.lower(), idx)
                if pos == -1:
                    break
                start = max(pos - 40, 0)
                end = min(pos + len(w) + 60, len(text))
                snippet = text[start:end].replace("\n", " ").strip()
                matches.append({
                    "word": w,
                    "type": kw.type,
                    "page": page_num,
                    "snippet": highlight_snippet(snippet, w),
                })
                idx = pos + len(w)
    return matches

# ---------------- Routes ----------------
@app.route("/", methods=["GET"])
def index():
    keywords = Keyword.query.order_by(Keyword.id.asc()).all()
    return render_template("index.html", keywords=keywords)

@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    if not files:
        return "No files uploaded", 400

    keywords = Keyword.query.all()
    results = []
    pos_count = 0
    neg_count = 0

    for f in files:
        if f.filename == "":
            continue
        if not allowed_file(f.filename):
            continue

        filename = secure_filename(f.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        f.save(path)

        if filename.lower().endswith(".pdf"):
            pages = extract_text_from_pdf(path)
        else:
            pages = extract_text_from_image(path)

        matches = search_keywords(pages, keywords)
        pos_count += sum(1 for m in matches if m["type"] == "positive")
        neg_count += sum(1 for m in matches if m["type"] == "negative")

        results.append({
            "filename": filename,
            "matches": matches
        })

    summary = {"positive": pos_count, "negative": neg_count, "total": pos_count + neg_count}
    return render_template("results.html", results=results, summary=summary)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = (request.form.get("keyword") or request.form.get("word") or "").strip()
    ktype = (request.form.get("type") or "").strip().lower()
    if not word or ktype not in {"positive", "negative"}:
        return redirect(url_for("index"))

    existing = Keyword.query.filter(Keyword.word.ilike(word)).first()
    if existing:
        return redirect(url_for("index"))

    db.session.add(Keyword(word=word, type=ktype))
    db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:id>", methods=["POST"])
def delete_keyword(id):
    # Optional password-protect deletion
    password = request.form.get("password", "")
    if password != os.getenv("DELETE_PASSWORD", "secret123"):
        return jsonify({"error": "Invalid password"}), 403

    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    return redirect(url_for("index"))

# Health check (optional)
@app.route("/healthz")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=True)
