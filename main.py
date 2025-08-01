import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_PATH = 'keywords.db'

# Ensure the database and table exist
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('positive', 'negative'))
            )
        ''')
        conn.commit()

init_db()

def get_keywords_by_type(keyword_type):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT id, word FROM keywords WHERE type = ?", (keyword_type,))
        return c.fetchall()

def add_keywords(words, keyword_type):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        for word in words:
            c.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (word.strip(), keyword_type))
        conn.commit()

def delete_keyword(keyword_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
        conn.commit()

def edit_keyword(keyword_id, new_word):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE keywords SET word = ? WHERE id = ?", (new_word, keyword_id))
        conn.commit()

def extract_keyword_matches(pdf_path, pos_keywords, neg_keywords):
    results = []
    counts = {}
    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        matches = []
        for word in pos_keywords + neg_keywords:
            word_lower = word.lower()
            count = text.lower().count(word_lower)
            if count > 0:
                matches.append((word, count))
                counts[word] = counts.get(word, 0) + count
                # Highlight the keyword
                for inst in page.search_for(word, hit_max=1000):
                    highlight = page.add_highlight_annot(inst)
                    highlight.update()
        if matches:
            results.append({
                'page': page_num,
                'matches': matches
            })

    highlighted_pdf = pdf_path.replace(".pdf", "_highlighted.pdf")
    doc.save(highlighted_pdf, garbage=4, deflate=True)
    doc.close()
    return results, counts, highlighted_pdf

@app.route('/', methods=['GET', 'POST'])
def index():
    pos_keywords = [k[1] for k in get_keywords_by_type("positive")]
    neg_keywords = [k[1] for k in get_keywords_by_type("negative")]
    pos_keywords_db = get_keywords_by_type("positive")
    neg_keywords_db = get_keywords_by_type("negative")
    results = []
    counts = {}
    highlighted_pdf = None

    if request.method == 'POST':
        uploaded_file = request.files['pdf']
        if uploaded_file.filename.endswith('.pdf'):
            filename = secure_filename(uploaded_file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(pdf_path)

            pos_input = request.form.get('positive_keywords', '')
            neg_input = request.form.get('negative_keywords', '')

            pos_new = [word.strip() for word in pos_input.split(',') if word.strip()]
            neg_new = [word.strip() for word in neg_input.split(',') if word.strip()]

            add_keywords(pos_new, 'positive')
            add_keywords(neg_new, 'negative')

            pos_keywords.extend(pos_new)
            neg_keywords.extend(neg_new)

            results, counts, highlighted_pdf = extract_keyword_matches(pdf_path, pos_keywords, neg_keywords)

    return render_template(
        'index.html',
        pos_keywords=pos_keywords_db,
        neg_keywords=neg_keywords_db,
        results=results,
        counts=counts,
        highlighted_pdf=highlighted_pdf
    )

@app.route('/delete_keyword/<int:keyword_id>', methods=['POST'])
def delete(keyword_id):
    delete_keyword(keyword_id)
    return redirect(url_for('index'))

@app.route('/edit_keyword/<int:keyword_id>', methods=['POST'])
def edit(keyword_id):
    new_word = request.form['new_word']
    edit_keyword(keyword_id, new_word)
    return redirect(url_for('index'))

@app.route('/highlighted/<filename>')
def download_highlighted(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
