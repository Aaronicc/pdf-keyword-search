import os
import pdfplumber
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup

app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///keywords.db"  # switch to postgres in Render
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Allowed extensions
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # positive or negative

with app.app_context():
    db.create_all()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def highlight_text(text, keywords):
    """Highlight keywords in extracted text"""
    if not text:
        return text
    highlighted = text
    for kw in keywords:
        highlighted = highlighted.replace(
            kw.word,
            f"<mark style='background-color: {'lightgreen' if kw.type=='positive' else 'salmon'};'>{kw.word}</mark>"
        )
    return Markup(highlighted)

@app.route("/", methods=["GET", "POST"])
def index():
    extracted_text = None
    highlighted_text = None

    if request.method == "POST":
        if "file" not in request.files:
            return redirect(request.url)

        file = request.files["file"]

        if file.filename == "":
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            ext = filename.rsplit(".", 1)[1].lower()

            # Extract text depending on file type
            if ext == "pdf":
                text = ""
                with pdfplumber.open(filepath) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
            else:  # image
                img = Image.open(filepath)
                text = pytesseract.image_to_string(img)

            # Highlight using keywords
            keywords = Keyword.query.all()
            highlighted_text = highlight_text(text, keywords)

    return render_template("index.html", extracted_text=highlighted_text)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("word")
    ktype = request.form.get("type")
    if word and ktype in ["positive", "negative"]:
        if not Keyword.query.filter_by(word=word).first():
            db.session.add(Keyword(word=word, type=ktype))
            db.session.commit()
    return redirect(url_for("manage_keywords"))

@app.route("/delete_keyword/<int:id>")
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    return redirect(url_for("manage_keywords"))

@app.route("/manage_keywords")
def manage_keywords():
    keywords = Keyword.query.all()
    return render_template("manage_keywords.html", keywords=keywords)

if __name__ == "__main__":
    app.run(debug=True)
