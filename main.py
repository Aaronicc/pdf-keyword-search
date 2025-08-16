import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Home page
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            flash("No file selected", "error")
            return redirect(request.url)

        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        keywords = [k.word for k in Keyword.query.all()]

        if file.filename.lower().endswith('.pdf'):
            results = search_pdf(filename, keywords)
        elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            results = search_image(filename, keywords)
        else:
            flash("Unsupported file type", "error")

    all_keywords = Keyword.query.all()
    return render_template('index.html', results=results, keywords=all_keywords)

# PDF search
def search_pdf(filepath, keywords):
    doc = fitz.open(filepath)
    matches = []

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        for kw in keywords:
            if kw.lower() in text.lower():
                snippet = get_snippet(text, kw)
                matches.append({'keyword': kw, 'page': page_num, 'snippet': snippet})
    return matches

# Image search
def search_image(filepath, keywords):
    img = Image.open(filepath)
    text = pytesseract.image_to_string(img)
    matches = []
    for kw in keywords:
        if kw.lower() in text.lower():
            matches.append({'keyword': kw, 'image': os.path.basename(filepath)})
    return matches

# Helper to get snippet around keyword
def get_snippet(text, keyword, radius=30):
    idx = text.lower().find(keyword.lower())
    start = max(idx - radius, 0)
    end = min(idx + len(keyword) + radius, len(text))
    return text[start:end].replace('\n', ' ')

# Add keyword
@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form.get('keyword')
    if word:
        existing = Keyword.query.filter_by(word=word).first()
        if existing:
            flash(f"Keyword '{word}' already exists.", "error")
        else:
            new_kw = Keyword(word=word)
            db.session.add(new_kw)
            db.session.commit()
            flash(f"Keyword '{word}' added.", "success")
    return redirect(url_for('index'))

# Delete keyword
@app.route('/delete_keyword/<int:kw_id>', methods=['POST'])
def delete_keyword(kw_id):
    kw = Keyword.query.get_or_404(kw_id)
    db.session.delete(kw)
    db.session.commit()
    flash(f"Keyword '{kw.word}' deleted.", "success")
    return redirect(url_for('index'))

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
