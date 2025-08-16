from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageOps
import io

app = Flask(__name__)
app.secret_key = "your-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///keywords.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Database model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Ensure tables exist
with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def index():
    all_keywords = Keyword.query.all()
    results = []

    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("Please upload a PDF or image file.", "error")
            return redirect(request.url)

        filename = file.filename.lower()
        extracted_text = ""

        try:
            # PDF file
            if filename.endswith(".pdf"):
                pdf_doc = fitz.open(stream=file.read(), filetype="pdf")
                for page in pdf_doc:
                    extracted_text += page.get_text()
            # Image file
            elif filename.endswith((".png", ".jpg", ".jpeg")):
                img = Image.open(file.stream)
                img = ImageOps.grayscale(img)  # Grayscale
                img = img.point(lambda x: 0 if x < 140 else 255, '1')  # B/W threshold
                extracted_text = pytesseract.image_to_string(img)
            else:
                flash("Unsupported file type.", "error")
                return redirect(request.url)

            # Normalize text
            extracted_text = " ".join(extracted_text.split())

            # Search keywords
            for kw in all_keywords:
                if kw.word.lower() in extracted_text.lower():
                    results.append(kw.word)

            if not results:
                flash("No keywords found.", "info")
            else:
                flash(f"Found keywords: {', '.join(results)}", "success")

        except Exception as e:
            flash(f"Error processing file: {e}", "error")

    return render_template("index.html", keywords=all_keywords, results=results)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    new_word = request.form.get("keyword")
    if not new_word:
        flash("Keyword cannot be empty.", "error")
        return redirect(url_for("index"))

    if Keyword.query.filter_by(word=new_word).first():
        flash("Keyword already exists.", "error")
        return redirect(url_for("index"))

    db.session.add(Keyword(word=new_word))
    db.session.commit()
    flash("Keyword added successfully.", "success")
    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:id>", methods=["POST"])
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    flash("Keyword deleted.", "success")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
