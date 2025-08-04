import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ADMIN_PASSWORD = 'Santiago01'
DATABASE = 'keywords.db'

def initialize_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

initialize_db()

def get_keywords():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT keyword, type FROM keywords")
    keywords = c.fetchall()
    pos_keywords = [kw[0] for kw in keywords if kw[1] == 'positive']
    neg_keywords = [kw[0] for kw in keywords if kw[1] == 'negative']
    conn.close()
    return pos_keywords, neg_keywords

def extract_keyword_matches(pdf_path, pos_keywords, neg_keywords):
    doc = fitz.open(pdf_path)
    results = []
    summary_count = {'positive': {}, 'negative': {}}

    for page_num, page in enumerate(doc, start=1):
        lines = page.get_text().split('\n')
        found_positive, found_negative = set(), set()
        line_matches = []

        for line in lines:
            lower_line = line.lower()
            line_pos = [kw for kw in pos_keywords if kw.lower() in lower_line]
            line_neg = [kw for kw in neg_keywords if kw.lower() in lower_line]
            if line_pos or line_neg:
                found_positive.update(line_pos)
                found_negative.update(line_neg)
                line_matches.append(line.strip())

                for kw in line_pos:
                    summary_count['positive'][kw] = summary_count['positive'].get(kw, 0) + 1
                for kw in line_neg:
                    summary_count['negative'][kw] = summary_count['negative'].get(kw, 0) + 1

        if found_positive or found_negative:
            results.append({
                'page': page_num,
                'found_positive': list(found_positive),
                'found_negative': list(found_negative),
                'lines': line_matches
            })

    return results, summary_count

@app.route('/', methods=['GET', 'POST'])
def index():
    pos_keywords, neg_keywords = get_keywords()
    results = []
    summary_count = {}

    if request.method == 'POST':
        file = request.files.get('pdf')
        if not file or file.filename == '':
            flash('No file selected')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(pdf_path)

        results, summary_count = extract_keyword_matches(pdf_path, pos_keywords, neg_keywords)

    return render_template(
        'index.html',
        pos_keywords=pos_keywords,
        neg_keywords=neg_keywords,
        results=results,
        summary_count=summary_count
    )

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword'].strip()
    type_ = request.form['type']
    if not keyword or type_ not in ['positive', 'negative']:
        return redirect(url_for('index'))

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM keywords WHERE LOWER(keyword) = LOWER(?)", (keyword,))
    if c.fetchone():
        flash(f"Keyword '{keyword}' already exists.")
    else:
        c.execute("INSERT INTO keywords (keyword, type) VALUES (?, ?)", (keyword, type_))
        conn.commit()
        flash(f"Keyword '{keyword}' added.")
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete_keyword/<string:keyword>', methods=['POST'])
def delete_keyword(keyword):
    password = request.form.get('password')
    if password != ADMIN_PASSWORD:
        flash('Incorrect password for deletion.')
        return redirect(url_for('index'))
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("DELETE FROM keywords WHERE keyword = ?", (keyword,))
    conn.commit()
    conn.close()
    flash(f"Keyword '{keyword}' deleted.")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
