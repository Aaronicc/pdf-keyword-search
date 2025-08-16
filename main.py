import os
from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

# --- Setup ---
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# SQLite database path
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'keywords.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Upload folder
UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Database Model ---
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    all_keywords = Keyword.query.all()
    results = []

    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)

            # Detect if PDF or Image
            if file.filename.lower().endswith('.pdf'):
                results = search_pdf(filepath)
            elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                results = search_image(filepath)

    return render_template('index.html', keywords=all_keywords, results=results)

# --- Keyword Routes ---
@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form.get('keyword')
    if word:
        existing = Keyword.query.filter_by(word=word).first()
        if not existing:
            db.session.add(Keyword(word=word))
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_keyword/<int:id>', methods=['POST'])
def delete_keyword(id):
    kw = Keyword.query.get(id)
    if kw:
        db.session.delete(kw)
        db.session.commit()
    return redirect(url_for('index'))

# --- Search Functions ---
def search_pdf(filepath):
    doc = fitz.open(filepath)
    keywords = [kw.word for kw in Keyword.query.all()]
    results = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        for kw in keywords:
            if kw.lower() in text.lower():
                results.append(f"Page {page_num}: {kw}")
    return results

def search_image(filepath):
    keywords = [kw.word for kw in Keyword.query.all()]
    results = []

    img = Image.open(filepath)
    text = pytesseract.image_to_string(img)
    for kw in keywords:
        if kw.lower() in text.lower():
            results.append(f"{kw} found in image")
    return results

# --- Main ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure table exists
    app.run(debug=True)
