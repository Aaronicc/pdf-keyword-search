import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# ---------------- Flask Setup ----------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Upload folder
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------- Database Model ----------------
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Ensure tables exist on startup
with app.app_context():
    db.create_all()

# ---------------- Helper Functions ----------------
def search_pdf_keywords(file_path):
    results = []
    doc = fitz.open(file_path)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        for kw in Keyword.query.all():
            if kw.word.lower() in text.lower():
                results.append({
                    'keyword': kw.word,
                    'page': page_num,
                    'snippet': get_snippet(text, kw.word)
                })
    return results

def search_image_keywords(file_path):
    results = []
    text = pytesseract.image_to_string(Image.open(file_path))
    for kw in Keyword.query.all():
        if kw.word.lower() in text.lower():
            results.append({
                'keyword': kw.word,
                'page': 1,
                'snippet': get_snippet(text, kw.word)
            })
    return results

def get_snippet(text, keyword, snippet_len=50):
    index = text.lower().find(keyword.lower())
    if index == -1:
        return ""
    start = max(index - snippet_len, 0)
    end = min(index + len(keyword) + snippet_len, len(text))
    return text[start:end].replace('\n', ' ')

# ---------------- Routes ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if 'file' not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No selected file")
            return redirect(request.url)
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            
            # Determine if PDF or image
            if file.filename.lower().endswith('.pdf'):
                results = search_pdf_keywords(file_path)
            else:
                results = search_image_keywords(file_path)

            return render_template("index.html", results=results, keywords=Keyword.query.all())

    all_keywords = Keyword.query.all()
    return render_template("index.html", keywords=all_keywords)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("keyword")
    if word:
        existing = Keyword.query.filter_by(word=word).first()
        if existing:
            flash(f"Keyword '{word}' already exists.")
        else:
            db.session.add(Keyword(word=word))
            db.session.commit()
            flash(f"Keyword '{word}' added successfully.")
    return redirect(url_for('index'))

@app.route("/delete_keyword/<int:keyword_id>", methods=["POST"])
def delete_keyword(keyword_id):
    kw = Keyword.query.get_or_404(keyword_id)
    db.session.delete(kw)
    db.session.commit()
    flash(f"Keyword '{kw.word}' deleted.")
    return redirect(url_for('index'))

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
