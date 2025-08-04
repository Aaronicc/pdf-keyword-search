import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ADMIN_PASSWORD = 'Santiago01'

# ✅ Initialize database

def initialize_db():
    conn = sqlite3.connect('keywords.db')
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

# ✅ Get keywords

def get_keywords():
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute("SELECT keyword, type FROM keywords")
    keywords = c.fetchall()
    pos_keywords = [kw[0] for kw in keywords if kw[1] == 'positive']
    neg_keywords = [kw[0] for kw in keywords if kw[1] == 'negative']
    conn.close()
    return pos_keywords, neg_keywords

# ✅ Highlight keywords and return compressed matches

def extract_keyword_matches(pdf_path, pos_keywords, neg_keywords):
    doc = fitz.open(pdf_path)
    results = []
    keyword_summary = {'positive': {}, 'negative': {}}

    for page_num, page in enumerate(doc, start=1):
        lines = page.get_text("text" + "lines").split('\n')
        matched_lines = []

        for line in lines:
            lower_line = line.lower()
            found_pos = [kw for kw in pos_keywords if kw.lower() in lower_line]
            found_neg = [kw for kw in neg_keywords if kw.lower() in lower_line]

            if found_pos or found_neg:
                # Highlight matched keywords in line
                highlighted = line
                for kw in found_pos + found_neg:
                    highlighted = highlighted.replace(kw, f'<mark>{kw}</mark>')

                matched_lines.append(highlighted.strip())

                for kw in found_pos:
                    keyword_summary['positive'][kw] = keyword_summary['positive'].get(kw, 0) + 1
                for kw in found_neg:
                    keyword_summary['negative'][kw] = keyword_summary['negative'].get(kw, 0) + 1

        if matched_lines:
            results.append({
                'page': page_num,
                'snippet': ' '.join(matched_lines)
            })

    return results, keyword_summary

# ✅ Home page

@app.route('/', methods=['GET', 'POST'])
def index():
    pos_keywords, neg_keywords = get_keywords()
    results = []
    keyword_summary = {'positive': {}, 'negative': {}}

    if request.method == 'POST':
        if 'pdf' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['pdf']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_path)
            results, keyword_summary = extract_keyword_matches(pdf_path, pos_keywords, neg_keywords)

    return render_template('index.html', pos_keywords=pos_keywords, neg_keywords=neg_keywords, results=results, keyword_summary=keyword_summary)

# ✅ Add keyword

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword'].strip()
    type_ = request.form['type']
    if keyword and type_ in ['positive', 'negative']:
        conn = sqlite3.connect('keywords.db')
        c = conn.cursor()
        c.execute("INSERT INTO keywords (keyword, type) VALUES (?, ?)", (keyword, type_))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

# ✅ Delete keyword

@app.route('/delete_keyword/<string:keyword>', methods=['POST'])
def delete_keyword(keyword):
    password = request.form.get('password')
    if password != ADMIN_PASSWORD:
        flash('Incorrect password for deletion.')
        return redirect(url_for('index'))
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute("DELETE FROM keywords WHERE keyword = ?", (keyword,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
