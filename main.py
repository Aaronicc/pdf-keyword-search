import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# === DB INIT ===
def init_db():
    conn = sqlite3.connect("keywords.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# === DB HELPERS ===
def get_keywords_by_type(keyword_type):
    conn = sqlite3.connect("keywords.db")
    c = conn.cursor()
    c.execute("SELECT word FROM keywords WHERE type = ?", (keyword_type,))
    words = [row[0] for row in c.fetchall()]
    conn.close()
    return words

def save_keyword(word, keyword_type):
    conn = sqlite3.connect("keywords.db")
    c = conn.cursor()
    c.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (word, keyword_type))
    conn.commit()
    conn.close()

# === PDF SEARCH ===
def extract_matches_from_pdf(pdf_path, pos_keywords, neg_keywords):
    results = []
    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            found_pos = [kw for kw in pos_keywords if kw.lower() in text.lower()]
            found_neg = [kw for kw in neg_keywords if kw.lower() in text.lower()]
            if found_pos or found_neg:
                results.append({
                    'page': page_num,
                    'found_positive': found_pos,
                    'found_negative': found_neg
                })
    return results

# === ROUTES ===
@app.route('/', methods=['GET', 'POST'])
def index():
    saved_pos_keywords = get_keywords_by_type("positive")
    saved_neg_keywords = get_keywords_by_type("negative")
    search_results = []

    if request.method == 'POST':
        if 'pdf' in request.files:
            pdf = request.files['pdf']
            if pdf.filename:
                filename = secure_filename(pdf.filename)
                pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                pdf.save(pdf_path)

                # Search using saved keywords
                search_results = extract_matches_from_pdf(pdf_path, saved_pos_keywords, saved_neg_keywords)

    return render_template('index.html',
                           pos_keywords=saved_pos_keywords,
                           neg_keywords=saved_neg_keywords,
                           results=search_results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = request.form.get('keyword')
    keyword_type = request.form.get('type')
    if word and keyword_type in ['positive', 'negative']:
        save_keyword(word.strip(), keyword_type)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
