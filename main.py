from flask import Flask, render_template, request, redirect, url_for
from models import db, Keyword
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///keywords.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)

@app.before_first_request
def create_tables():
    db.create_all()

def extract_text_from_pdf(file_path):
    text = ""
    pdf = fitz.open(file_path)
    for page in pdf:
        text += page.get_text()
    return text

def extract_text_from_image(file_path):
    img = Image.open(file_path)
    return pytesseract.image_to_string(img)

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    if request.method == "POST":
        file = request.files["file"]
        if file:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(file_path)
            
            if file.filename.lower().endswith(".pdf"):
                text = extract_text_from_pdf(file_path)
            else:
                text = extract_text_from_image(file_path)

            keywords = Keyword.query.all()
            for kw in keywords:
                if kw.word.lower() in text.lower():
                    results.append({"word": kw.word, "positive": kw.positive})
    keywords_list = Keyword.query.all()
    return render_template("index.html", results=results, keywords=keywords_list)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form["word"]
    positive = request.form.get("positive") == "true"
    if not Keyword.query.filter_by(word=word).first():
        new_kw = Keyword(word=word, positive=positive)
        db.session.add(new_kw)
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:id>", methods=["POST"])
def delete_keyword(id):
    kw = Keyword.query.get(id)
    if kw:
        db.session.delete(kw)
        db.session.commit()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
