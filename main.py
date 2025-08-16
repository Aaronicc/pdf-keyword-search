import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Upload folder setup (safe creation)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.isdir(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Keyword model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    all_keywords = Keyword.query.all()
    if request.method == 'POST':
        pdf_file = request.files.get('pdf_file')
        if pdf_file:
            filename = secure_filename(pdf_file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(file_path)

            # Extract text from PDF using PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()

            # Search for keywords
            for kw in all_keywords:
                if kw.word.lower() in text.lower():
                    results.append({'keyword': kw.word, 'found': True})
                else:
                    results.append({'keyword': kw.word, 'found': False})

    return render_template('index.html', keywords=all_keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form.get('keyword')
    if word:
        if not Keyword.query.filter_by(word=word).first():
            new_kw = Keyword(word=word)
            db.session.add(new_kw)
            db.session.commit()
    return redirect(url_for('index'))

@app.route('/delete_keyword/<int:id>', methods=['POST'])
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
