import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import PyPDF2

# Initialize Flask
app = Flask(__name__)
app.secret_key = "supersecretkey"

# =========================
# Database Configuration
# =========================
database_url = os.environ.get("DATABASE_URL")

if database_url:
    # Render gives DATABASE_URL starting with postgres://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    # Fallback to local SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///keywords.db"

db = SQLAlchemy(app)

# =========================
# Database Model
# =========================
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(120), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # "positive" or "negative"

# =========================
# File Upload Settings
# =========================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# =========================
# OCR & PDF Processing
# =========================
def extract_text_from_image(image_path):
    img = Image.open(image_path)
    return pytesseract.image_to_string(img)

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

# =========================
# Routes
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "files[]" not in request.files:
            flash("No file part")
            return redirect(request.url)

        files = request.files.getlist("files[]")
        all_texts = []

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                if filename.lower().endswith(".pdf"):
                    all_texts.append(extract_text_from_pdf(filepath))
                else:
                    all_texts.append(extract_text_from_image(filepath))

        combined_text = "\n".join(all_texts)

        keywords = Keyword.query.all()
        results = []
        for kw in keywords:
            if kw.word.lower() in combined_text.lower():
                results.append((kw.word, kw.type))

        return render_template("results.html", results=results, text_preview=combined_text[:1000])

    keywords = Keyword.query.all()
    return render_template("index.html", keywords=keywords)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("word").strip()
    type_ = request.form.get("type")

    if not word or not type_:
        flash("Please provide a keyword and type.")
        return redirect(url_for("index"))

    if Keyword.query.filter_by(word=word).first():
        flash("Keyword already exists!")
        return redirect(url_for("index"))

    new_kw = Keyword(word=word, type=type_)
    db.session.add(new_kw)
    db.session.commit()
    flash("Keyword added successfully!")
    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:kw_id>", methods=["POST"])
def delete_keyword(kw_id):
    kw = Keyword.query.get_or_404(kw_id)
    db.session.delete(kw)
    db.session.commit()
    flash("Keyword deleted successfully!")
    return redirect(url_for("index"))

# =========================
# App Runner
# =========================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
