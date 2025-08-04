import os
import fitz  # PyMuPDF
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads'
PASSWORD = "adminpass"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = 'keywords.db'

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS keywords (
                        keyword TEXT PRIMARY KEY,
                        type TEXT CHECK(type IN ('positive', 'negative'))
                    )''')
        conn.commit()

init_db()

def load_keywords():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT keyword, type FROM keywords")
        rows = c.fetchall()
        pos_keywords = [r[0] for r in rows if r[1] == 'positive']
        neg_keywords = [r[0] for r in rows if r[1] == 'negative']
    return pos_keywords, neg_keywords

def add_keyword_to_db(keyword, kw_type):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO keywords (keyword, type) VALUES (?, ?)", (keyword.lower(), kw_type))
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False

def delete_keyword_from_db(keyword):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM keywords WHERE keyword = ?", (keyword.lower(),))
        conn.commit()

def extract_keyword_matches(pdf_path, pos_keywords, neg_keywords):
    results = []
    summary_count = {"positive": {}, "negative": {}}

    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        page_result = {"page": page_num, "found_positive": [], "found_negative": [], "lines": []}

        for line in lines:
            line_lower = line.lower()
            found_pos = [kw for kw in pos_keywords if kw.lower() in line_lower]
            found_neg = [kw for kw in neg_keywords if kw.lower() in line_lower]

            if found_pos or found_neg:
                page_result["lines"].append(line)
                for kw in found_pos:
                    if kw not in page_result["found_positive"]:
                        page_result["found_positive"].append(kw)
                        summary_count['positive'][kw] = summary_count['positive'].get(kw, 0) + 1
                for kw in found_neg:
                    if kw not in page_result["found_negative"]:
                        page_result["found_negative"].append(kw)
                        summary_count['negative'][kw] = summary_count['negative'].get(kw, 0) + 1

        if page_result["lines"]:
            results.append(page_result)

    return results, summary_count

@app.route('/', methods=['GET', 'POST'])
def index():
    pos_keywords, neg_keywords = load_keywords()
    results = []
    summary_count = None

    if request.method == 'POST':
        pdf = request.files['pdf']
        if pdf and pdf.filename.endswith('.pdf'):
            filename = secure_filename(pdf.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf.save(pdf_path)

            results, summary_count = extract_keyword_matches(pdf_path, pos_keywords, neg_keywords)

    return render_template('index.html', pos_keywords=pos_keywords, neg_keywords=neg_keywords,
                           results=results, summary_count=summary_count)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword'].strip()
    kw_type = request.form['type']

    if not add_keyword_to_db(keyword, kw_type):
        flash(f"Keyword '{keyword}' already exists!", 'error')

    return redirect(url_for('index'))

@app.route('/delete_keyword/<keyword>', methods=['POST'])
def delete_keyword(keyword):
    password = request.form.get('password', '')
    if password != PASSWORD:
        flash('Incorrect password for deletion.', 'error')
        return redirect(url_for('index'))

    delete_keyword_from_db(keyword)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
