import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract
from werkzeug.utils import secure_filename

# Flask app setup
app = Flask(__name__)
app.secret_key = "your_secret_key"
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Database setup
db = SQLAlchemy(app)

class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    all_keywords = Keyword.query.all()
    results = []
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part")
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash("No selected file")
            return redirect(request.url)
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract text from PDF
        text = ""
        try:
            doc = fitz.open(filepath)
            for page in doc:
                text += page.get_text()
            doc.close()
        except Exception:
            # Try OCR on PDF pages if normal extraction fails
            pages = convert_from_path(filepath)
            for page in pages:
                text += pytesseract.image_to_string(page)

        # If it's an image file, use OCR
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            text += pytesseract.image_to_string(filepath)

        # Search keywords
        for keyword in all_keywords:
            if keyword.word.lower() in text.lower():
                results.append(keyword.word)

        flash(f"Found keywords: {', '.join(results)}" if results else "No matches found")
    return render_template('index.html', keywords=all_keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form.get('keyword')
    if not word:
        flash("Please enter a keyword")
        return redirect(url_for('index'))
    if Keyword.query.filter_by(word=word).first():
        flash("Keyword already exists")
        return redirect(url_for('index'))
    new_kw = Keyword(word=word)
    db.session.add(new_kw)
    db.session.commit()
    flash("Keyword added")
    return redirect(url_for('index'))

@app.route('/delete_keyword/<int:id>', methods=['POST'])
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    flash("Keyword deleted")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
