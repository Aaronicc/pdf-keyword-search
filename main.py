import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Database setup
uri = os.getenv("DATABASE_URL", "sqlite:///keywords.db")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

with app.app_context():
    db.create_all()

def extract_text_from_image(path):
    image = Image.open(path)
    return pytesseract.image_to_string(image)

def extract_text_from_pdf(path):
    pages = convert_from_path(path)
    text = ""
    for page in pages:
        text += pytesseract.image_to_string(page)
    return text

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        keyword = request.form.get("keyword")
        if keyword:
            if not Keyword.query.filter_by(word=keyword).first():
                db.session.add(Keyword(word=keyword))
                db.session.commit()
        return redirect(url_for("index"))
    keywords = Keyword.query.all()
    return render_template("index.html", keywords=keywords)

@app.route("/search", methods=["POST"])
def search():
    uploaded_files = request.files.getlist("files")
    keywords = [k.word for k in Keyword.query.all()]
    results = {}

    for file in uploaded_files:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(filepath)
        else:
            text = extract_text_from_image(filepath)

        found = [kw for kw in keywords if kw.lower() in text.lower()]
        results[filename] = found

    return render_template("results.html", results=results, keywords=keywords)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
