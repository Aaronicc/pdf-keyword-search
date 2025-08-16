from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF for PDF text extraction
from PIL import Image, ImageOps
import pytesseract
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///keywords.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Keyword model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Ensure database and table exist
with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def index():
    all_keywords = Keyword.query.all()
    matched_keywords = []
    extracted_text = ""
    page_snippets = []

    if request.method == "POST":
        file = request.files["file"]
        if file:
            filename = file.filename.lower()
            
            # PDF processing
            if filename.endswith(".pdf"):
                doc = fitz.open(stream=file.read(), filetype="pdf")
                for page_number, page in enumerate(doc, start=1):
                    text = page.get_text()
                    for kw in all_keywords:
                        if kw.word.lower() in text.lower():
                            matched_keywords.append(kw.word)
                            snippet = text.lower().split(kw.word.lower(), 1)[0][-50:] + kw.word + text.lower().split(kw.word.lower(), 1)[1][:50]
                            page_snippets.append(f"Page {page_number}: ...{snippet}...")
                    extracted_text += text

            # Image processing
            elif filename.endswith((".png", ".jpg", ".jpeg")):
                img = Image.open(file.stream)
                img = ImageOps.grayscale(img)

                # Resize for better OCR
                base_width = 1800
                w_percent = (base_width / float(img.size[0]))
                h_size = int((float(img.size[1]) * float(w_percent)))
                img = img.resize((base_width, h_size), Image.LANCZOS)

                # Adaptive threshold for clearer OCR
                img = img.point(lambda x: 0 if x < 160 else 255, '1')

                text = pytesseract.image_to_string(img, lang='eng')
                extracted_text = text

                for kw in all_keywords:
                    if kw.word.lower() in text.lower():
                        matched_keywords.append(kw.word)
                        snippet = text.lower().split(kw.word.lower(), 1)[0][-50:] + kw.word + text.lower().split(kw.word.lower(), 1)[1][:50]
                        page_snippets.append(f"Image: ...{snippet}...")

    return render_template("index.html", keywords=all_keywords, matched=matched_keywords, snippets=page_snippets)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    new_kw = request.form.get("keyword")
    if new_kw:
        if not Keyword.query.filter_by(word=new_kw).first():
            db.session.add(Keyword(word=new_kw))
            db.session.commit()
            flash(f"Keyword '{new_kw}' added.", "success")
        else:
            flash("Keyword already exists.", "warning")
    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:kw_id>", methods=["POST"])
def delete_keyword(kw_id):
    kw = Keyword.query.get_or_404(kw_id)
    db.session.delete(kw)
    db.session.commit()
    flash(f"Keyword '{kw.word}' deleted.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
