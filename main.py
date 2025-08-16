from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///keywords.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Model ---
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), nullable=False, unique=True)

# --- Initialize DB ---
with app.app_context():
    db.create_all()

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def index():
    keywords = Keyword.query.all()
    results = []

    if request.method == 'POST':
        pdf_file = request.files.get('pdf')
        if pdf_file:
            pdf_bytes = pdf_file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            for page_num, page in enumerate(doc, start=1):
                # --- Extract text ---
                text = page.get_text()

                # --- Extract images and OCR ---
                for img_index, img in enumerate(page.get_images(full=True)):
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n < 5:  # grayscale or RGB
                        img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    else:  # CMYK
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                        img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text += " " + pytesseract.image_to_string(img_pil)

                # --- Search for keywords ---
                for kw in keywords:
                    if kw.word.lower() in text.lower():
                        index = text.lower().find(kw.word.lower())
                        snippet = text[max(0, index-30):index+30]
                        results.append({
                            "keyword": kw.word,
                            "page": page_num,
                            "snippet": snippet
                        })

    return render_template('index.html', keywords=keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form.get('keyword')
    if word and not Keyword.query.filter_by(word=word).first():
        new_kw = Keyword(word=word)
        db.session.add(new_kw)
        db.session.commit()
    return redirect('/')

@app.route('/delete_keyword/<int:id>', methods=['POST'])
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    return ('', 204)

@app.route('/edit_keyword/<int:id>', methods=['POST'])
def edit_keyword(id):
    data = request.get_json()
    kw = Keyword.query.get_or_404(id)
    kw.word = data['word']
    db.session.commit()
    return ('', 204)

# --- Run App ---
if __name__ == '__main__':
    app.run(debug=True)
