# This is for cross-reference purposes only and should not be used as the sole basis for your review.

import os
import fitz  # PyMuPDF
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
DB_FILE = 'keywords.db'


# === DB Setup ===
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
            )
        ''')
        conn.commit()

init_db()


# === Keyword Utilities ===
def add_keyword(word, keyword_type):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (word.strip(), keyword_type))
        conn.commit()

def get_keywords_by_type(keyword_type):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT word FROM keywords WHERE type = ?", (keyword_type,))
        return [row[0] for row in c.fetchall()]


# === PDF Search ===
def extract_keyword_matches(pdf_path, positive_keywords, negative_keywords):
    results = []
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return [], f"Error opening PDF: {e}"

    positive_counts = {kw.lower(): 0 for kw in positive_keywords}
    negative_counts = {kw.lower(): 0 for kw in negative_keywords}

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            matched_keywords = []
            for kw in positive_keywords:
                if kw.lower() in line_lower:
                    positive_counts[kw.lower()] += 1
                    matched_keywords.append(kw)
            for kw in negative_keywords:
                if kw.lower() in line_lower:
                    negative_counts[kw.lower()] += 1
                    matched_keywords.append(kw)
            if matched_keywords:
                results.append((page_num, line.strip(), matched_keywords))

    doc.close()
    return results, {"positive": positive_counts, "negative": negative_counts}


# === Routes ===
@app.route('/', methods=['GET', 'POST'])
def index():
    saved_pos_keywords = get_keywords_by_type("positive")
    saved_neg_keywords = get_keywords_by_type("negative")
    results = []
    match_counts = {}
    message = ""

    if request.method == 'POST':
        if 'add_positive' in request.form:
            new_kw = request.form.get('positive_keyword', '').strip()
            if new_kw:
                add_keyword(new_kw, 'positive')
            return redirect(url_for('index'))

        elif 'add_negative' in request.form:
            new_kw = request.form.get('negative_keyword', '').strip()
            if new_kw:
                add_keyword(new_kw, 'negative')
            return redirect(url_for('index'))

        elif 'pdf' in request.files:
            pdf_file = request.files['pdf']
            if pdf_file.filename != '':
                filename = secure_filename(pdf_file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                pdf_file.save(filepath)

                results, match_counts = extract_keyword_matches(
                    filepath, saved_pos_keywords, saved_neg_keywords
                )

                if isinstance(match_counts, str):  # If error message returned
                    message = match_counts

    return render_template('index.html',
                           saved_pos_keywords=saved_pos_keywords,
                           saved_neg_keywords=saved_neg_keywords,
                           results=results,
                           match_counts=match_counts,
                           message=message)


if __name__ == '__main__':
    app.run(debug=True)
