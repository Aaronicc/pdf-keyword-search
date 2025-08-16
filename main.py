import os
from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Ensure DB exists
with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def index():
    all_keywords = Keyword.query.all()
    results = []

    if request.method == 'POST':
        file = request.files.get('pdf')
        if file:
            filepath = os.path.join('uploads', file.filename)
            os.makedirs('uploads', exist_ok=True)
            file.save(filepath)

            # PDF text search
            doc = fitz.open(filepath)
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                for kw in all_keywords:
                    if kw.word.lower() in text.lower():
                        results.append({
                            'keyword': kw.word,
                            'page': page_num,
                            'snippet': text[:200]
                        })

            # Image search
            images = convert_from_path(filepath)
            for i, img in enumerate(images, start=1):
                img_text = pytesseract.image_to_string(img)
                for kw in all_keywords:
                    if kw.word.lower() in img_text.lower():
                        results.append({
                            'keyword': kw.word,
                            'page': f'image {i}',
                            'snippet': img_text[:200]
                        })

    return render_template('index.html', keywords=all_keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form.get('keyword')
    if word:
        if not Keyword.query.filter_by(word=word).first():
            db.session.add(Keyword(word=word))
            db.session.commit()
    return ('', 204)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
