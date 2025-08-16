import os
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String
import pytesseract
from PIL import Image
import PyPDF2

# --- Flask setup ---
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# --- Database setup ---
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///keywords.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# --- Model ---
class Keyword(db.Model):
    id = Column(Integer, primary_key=True)
    word = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # "positive" or "negative"

with app.app_context():
    db.create_all()

# --- Helper functions ---
def extract_text_from_pdf(filepath):
    text = ""
    with open(filepath, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def extract_text_from_image(filepath):
    img = Image.open(filepath)
    return pytesseract.image_to_string(img)

def search_text(text, keywords):
    results = []
    for kw in keywords:
        if kw.word.lower() in text.lower():
            results.append({
                "keyword": kw.word,
                "type": kw.type
            })
    return results

# --- Routes ---
@app.route("/")
def index():
    keywords = Keyword.query.all()
    return render_template("index.html", keywords=keywords)

@app.route("/upload", methods=["POST"])
def upload():
    uploaded_files = request.files.getlist("files")
    if not uploaded_files or uploaded_files[0].filename == "":
        return "No file uploaded", 400

    keywords = Keyword.query.all()
    all_results = []

    for file in uploaded_files:
        filename = file.filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Extract text
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(filepath)
        else:
            text = extract_text_from_image(filepath)

        # Search
        results = search_text(text, keywords)
        all_results.append({
            "filename": filename,
            "results": results
        })

    return render_template("results.html", results=all_results)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("word")
    ktype = request.form.get("type")

    if not word or not ktype:
        return "Missing fields", 400

    existing = Keyword.query.filter_by(word=word).first()
    if existing:
        return "Keyword already exists", 400

    new_kw = Keyword(word=word, type=ktype)
    db.session.add(new_kw)
    db.session.commit()
    return "Keyword added successfully"

if __name__ == "__main__":
    app.run(debug=True)
