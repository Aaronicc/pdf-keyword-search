import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = 'keywords.db'

# Initialize DB if not exists
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS keywords (
                        keyword TEXT PRIMARY KEY,
                        type TEXT CHECK(type IN ('positive', 'negative'))
                    )''')
        conn.commit()

init_db()

def get_keywords():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT keyword FROM keywords WHERE type='positive'")
        pos = [row[0] for row in c.fetchall()]
        c.execute("SELECT keyword FROM keywords WHERE type='negative'")
        neg = [row[0] for row in c.fetchall()]
        return pos, neg

def add_keyword_to_db(keyword, ktype):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO keywords (keyword, type) VALUES (?, ?)", (keyword, ktype))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def delete_keyword_from_db(keyword):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM keywords WHERE keyword=?", (keyword,))
        conn.commit()

def extract_keyword_matches(pdf_path, pos_keywords, neg_keywords):
    results = []
    summary_count = {"positive": {}, "negative": {}}

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text()
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            found_pos = []
            found_neg = []
            matched_lines = []

            for line in lines:
                lower_line = line.lower()
                matched = False

                for kw in pos_keywords:
                    if kw.lower() in lower_line:
                        if kw not in found_pos:
                            found_pos.append(kw)
                        summary_count['positive'][kw] = summary_count['positive'].get(kw, 0) + 1
                        matched = True

                for kw in neg_keywords:
                    if kw.lower() in lower_line:
                        if kw not in found_neg:
                            found_neg.append(kw)
                        summary_count['negative'][kw] = summary_count['negative'].get(kw, 0) + 1
                        matched = True

                if matched:
                    matched_lines.append(line)

            if found_pos or found_neg:
                results.append({
                    'page': page_num,
                    'found_positive': found_pos,
                    'found_negative': found_neg,
                    'lines': matched_lines
                })

    return results, summary_count

@app.route('/', methods=['GET', 'POST'])
def index():
    pos_keywords, neg_keywords = get_keywords()
    results = []
    summary_count = {}

    if request.method == 'POST':
        if 'pdf' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['pdf']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        results, summary_count = extract_keyword_matches(filepath, pos_keywords, neg_keywords)
        flash('PDF uploaded and searched successfully!')

    return render_template('index.html', results=results, pos_keywords=pos_keywords,
                           neg_keywords=neg_keywords, summary_count=summary_count)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword'].strip()
    ktype = request.form['type']
    if not keyword:
        flash('Keyword cannot be empty')
    elif not add_keyword_to_db(keyword, ktype):
        flash('Keyword already exists')
    else:
        flash('Keyword added successfully')
    return redirect(url_for('index'))

@app.route('/delete/<keyword>', methods=['POST'])
def delete_keyword(keyword):
    password = request.form.get('password')
    if password == 'yourpassword':
        delete_keyword_from_db(keyword)
        flash('Keyword deleted')
    else:
        flash('Incorrect password')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
