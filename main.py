from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import pytesseract
from pdf2image import convert_from_path
import fitz  # PyMuPDF

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# --- Database config ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
db = SQLAlchemy(app)

# --- Models ---
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)

# --- Upload folder setup ---
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Routes ---
@app.route("/", methods=['GET', 'POST'])
def index():
    all_keywords = Keyword.query.all()
    results = []
    if request.method == 'POST':
        if 'pdf_file' in request.files:
            pdf_file = request.files['pdf_file']
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
            pdf_file.save(filepath)

            # Extract text from PDF using PyMuPDF
            doc = fitz.open(filepath)
            text = ""
            for page in doc:
                text += page.get_text()

            # Search keywords
            for kw in all_keywords:
                if kw.word.lower() in text.lower():
                    results.append(kw.word)
    return render_template('index.html', keywords=all_keywords, results=results)

@app.route("/add_keyword", methods=['POST'])
def add_keyword():
    new_kw = request.form.get('keyword')
    if new_kw:
        if not Keyword.query.filter_by(word=new_kw).first():
            db.session.add(Keyword(word=new_kw))
            db.session.commit()
    return redirect(url_for('index'))

@app.route("/delete_keyword/<int:id>", methods=['POST'])
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    return redirect(url_for('index'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
