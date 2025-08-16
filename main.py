from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
from PIL import Image, ImageOps
import pytesseract
import os
import cv2
import numpy as np

app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///keywords.db"
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db = SQLAlchemy(app)

# ----------------------------
# Database model
# ----------------------------
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

with app.app_context():
    db.create_all()

# ----------------------------
# OCR helper for images
# ----------------------------
def ocr_image(file_path):
    """Perform OCR on an image with preprocessing for better accuracy."""
    img = Image.open(file_path)
    img = ImageOps.grayscale(img)  # Convert to grayscale
    img_cv = np.array(img)
    img_cv = cv2.threshold(img_cv, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    # Resize small images
    h, w = img_cv.shape
    if w < 800:
        scale = 800 / w
        img_cv = cv2.resize(img_cv, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_LINEAR)

    img = Image.fromarray(img_cv)
    text = pytesseract.image_to_string(img)
    return " ".join(text.lower().split())

# ----------------------------
# PDF helper
# ----------------------------
def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return " ".join(text.lower().split())

# ----------------------------
# Routes
# ----------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    all_keywords = Keyword.query.all()
    results = []

    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("No file uploaded!", "error")
            return redirect(url_for("index"))

        filename = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filename)

        # Extract text based on file type
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(filename)
        elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
            text = ocr_image(filename)
        else:
            flash("Unsupported file type!", "error")
            return redirect(url_for("index"))

        # Search for keywords
        for kw in all_keywords:
            if kw.word.lower() in text:
                results.append(kw.word)

        if not results:
            flash("No matches found.", "info")

    return render_template("index.html", keywords=all_keywords, results=results)

# ----------------------------
# Add keyword
# ----------------------------
@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("keyword").strip()
    if word:
        existing = Keyword.query.filter_by(word=word).first()
        if existing:
            flash("Keyword already exists!", "error")
        else:
            db.session.add(Keyword(word=word))
            db.session.commit()
            flash("Keyword added!", "success")
    return redirect(url_for("index"))

# ----------------------------
# Delete keyword
# ----------------------------
@app.route("/delete_keyword/<int:kw_id>", methods=["POST"])
def delete_keyword(kw_id):
    kw = Keyword.query.get_or_404(kw_id)
    db.session.delete(kw)
    db.session.commit()
    flash("Keyword deleted.", "success")
    return redirect(url_for("index"))

# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
