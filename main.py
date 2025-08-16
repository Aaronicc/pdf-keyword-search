from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
import fitz  # PyMuPDF
import pytesseract
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Create upload folder if not exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    keyword = db.Column(db.String(100), nullable=False)

db.create_all()

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF, including OCR for scanned pages."""
    text = ""
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text()
        if not page_text.strip():
            # OCR fallback for scanned PDF
            images = convert_from_path(pdf_path, first_page=page_num+1, last_page=page_num+1)
            for image in images:
                page_text += pytesseract.image_to_string(image)
        text += page_text
    return text

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    all_keywords = Keyword.query.all()

    if request.method == 'POST':
        if 'pdf_file' in request.files:
            pdf_file = request.files['pdf_file']
            if pdf_file.filename != '':
                filename = secure_filename(pdf_file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                pdf_file.save(path)
                pdf_text = extract_text_from_pdf(path)

                # Search for keywords
                for kw in all_keywords:
                    if kw.keyword.lower() in pdf_text.lower():
                        results.append({'keyword': kw.keyword, 'found': True})
                    else:
                        results.append({'keyword': kw.keyword, 'found': False})

                flash(f'Searched {len(all_keywords)} keywords in {filename}', 'info')
                return render_template('index.html', keywords=all_keywords, results=results)

    return render_template('index.html', keywords=all_keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    kw_text = request.form.get('keyword')
    if kw_text:
        if Keyword.query.filter_by(keyword=kw_text).first():
            flash('Keyword already exists', 'warning')
        else:
            new_kw = Keyword(keyword=kw_text)
            db.session.add(new_kw)
            db.session.commit()
            flash('Keyword added', 'success')
    return redirect(url_for('index'))

@app.route('/delete_keyword/<int:id>', methods=['POST'])
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    flash('Keyword deleted', 'success')
    return redirect(url_for('index'))

@app.route('/edit_keyword/<int:id>', methods=['GET', 'POST'])
def edit_keyword(id):
    kw = Keyword.query.get_or_404(id)
    if request.method == 'POST':
        new_text = request.form.get('keyword')
        if new_text:
            kw.keyword = new_text
            db.session.commit()
            flash('Keyword updated', 'success')
            return redirect(url_for('index'))
    return render_template('edit.html', keyword=kw)

if __name__ == '__main__':
    app.run(debug=True)
