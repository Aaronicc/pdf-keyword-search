import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
import pytesseract
from PIL import Image, ImageEnhance
import cv2
import numpy as np

# -------------------- Configuration -------------------- #
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# -------------------- Database Model -------------------- #
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# Initialize DB (create tables if not exists)
with app.app_context():
    db.create_all()

# -------------------- Helper Functions -------------------- #
def preprocess_image(img_path):
    """Preprocess image for better OCR results."""
    img = Image.open(img_path).convert('L')  # Grayscale
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    img_np = np.array(img)
    _, img_thresh = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    img_blur = cv2.medianBlur(img_thresh, 3)
    return Image.fromarray(img_blur)

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def extract_text_from_image(img_path):
    """Extract text from image using pytesseract with preprocessing."""
    processed_img = preprocess_image(img_path)
    return pytesseract.image_to_string(processed_img)

# -------------------- Routes -------------------- #
@app.route('/', methods=['GET', 'POST'])
def index():
    all_keywords = Keyword.query.all()
    search_results = []
    uploaded_file = None

    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            uploaded_file = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            # Determine if PDF or image
            if file.filename.lower().endswith('.pdf'):
                text = extract_text_from_pdf(file_path)
            elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                text = extract_text_from_image(file_path)
            else:
                text = ""

            # Search for keywords
            for kw in all_keywords:
                if kw.word.lower() in text.lower():
                    search_results.append(kw.word)

    return render_template('index.html', keywords=all_keywords,
                           results=search_results, uploaded_file=uploaded_file)

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

@app.route('/delete_keyword/<int:kw_id>', methods=['POST'])
def delete_keyword(kw_id):
    kw = Keyword.query.get_or_404(kw_id)
    db.session.delete(kw)
    db.session.commit()
    return redirect(url_for('index'))

# -------------------- Run App -------------------- #
if __name__ == '__main__':
    app.run(debug=True)
