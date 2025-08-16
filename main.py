import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path

# ----------------------
# Flask app setup
# ----------------------
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'keywords.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Make sure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
db = SQLAlchemy(app)

# ----------------------
# Database model
# ----------------------
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False, unique=True)

# Create tables
with app.app_context():
    db.create_all()

# ----------------------
# Routes
# ----------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    all_keywords = Keyword.query.all()

    if request.method == 'POST':
        if 'pdf_file' in request.files:
            pdf_file = request.files['pdf_file']
            if pdf_file.filename != '':
                filename = secure_filename(pdf_file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                pdf_file.save(filepath)

                # Extract text from PDF (both text layer and images)
                text_content = ""
                # 1. Extract text from PDF pages
                doc = fitz.open(filepath)
                for page in doc:
                    text_content += page.get_text()
                # 2. Extract text from images using OCR
                images = convert_from_path(filepath)
                for img in images:
                    text_content += " " + pytesseract.image_to_string(img)

                # Search for keywords
                for kw in all_keywords:
                    if kw.word.lower() in text_content.lower():
                        results.append({'keyword': kw.word})
    
    return render_template('index.html', keywords=all_keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form.get('keyword')
    if word:
        existing = Keyword.query.filter_by(word=word).first()
        if not existing:
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

# ----------------------
# Run server
# ----------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
