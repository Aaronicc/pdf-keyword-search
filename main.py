from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SECRET_KEY'] = 'supersecret'
db = SQLAlchemy(app)

# Model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Create DB
with app.app_context():
    db.create_all()

# Extract text from PDF
def extract_pdf_text(file_path):
    doc = fitz.open(file_path)
    pdf_text = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pdf_text.append((i + 1, text))
    return pdf_text

# Extract text from Image
def extract_image_text(file_path):
    text = pytesseract.image_to_string(Image.open(file_path))
    return [(1, text)]

# Search keywords
def search_keywords(text_data):
    results = []
    keywords = Keyword.query.all()
    for page_num, text in text_data:
        for kw in keywords:
            if kw.word.lower() in text.lower():
                idx = text.lower().find(kw.word.lower())
                snippet = text[max(idx-30, 0): idx+30]
                results.append({
                    'keyword': kw.word,
                    'page': page_num,
                    'snippet': snippet
                })
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            flash('No file selected!')
            return redirect(request.url)
        os.makedirs('uploads', exist_ok=True)
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)

        if file.filename.lower().endswith('.pdf'):
            text_data = extract_pdf_text(file_path)
        else:
            text_data = extract_image_text(file_path)

        results = search_keywords(text_data)

    keywords = Keyword.query.all()
    return render_template('index.html', keywords=keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form['keyword'].strip()
    if not word:
        flash("Keyword cannot be empty")
    else:
        existing = Keyword.query.filter_by(word=word).first()
        if existing:
            flash("Keyword already exists")
        else:
            db.session.add(Keyword(word=word))
            db.session.commit()
            flash(f"Keyword '{word}' added")
    return redirect(url_for('index'))

@app.route('/delete_keyword/<int:keyword_id>', methods=['POST'])
def delete_keyword(keyword_id):
    kw = Keyword.query.get_or_404(keyword_id)
    db.session.delete(kw)
    db.session.commit()
    flash(f"Keyword '{kw.word}' deleted")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
