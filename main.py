import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, jsonify

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = 'keywords.db'

# Initialize DB
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
            )
        ''')
init_db()

# Get keywords from DB
def get_keywords_by_type(keyword_type):
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id, word FROM keywords WHERE type = ?", (keyword_type,))
        return c.fetchall()

@app.route('/')
def index():
    saved_pos_keywords = get_keywords_by_type("positive")
    saved_neg_keywords = get_keywords_by_type("negative")
    return render_template('index.html', pos_keywords=saved_pos_keywords, neg_keywords=saved_neg_keywords)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword']
    keyword_type = request.form['keyword_type']
    if keyword.strip():
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (keyword.strip(), keyword_type))
    return redirect('/')

@app.route('/delete_keyword/<int:keyword_id>', methods=['POST'])
def delete_keyword(keyword_id):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
    return redirect('/')

@app.route('/edit_keyword/<int:keyword_id>', methods=['POST'])
def edit_keyword(keyword_id):
    new_word = request.form['new_word']
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("UPDATE keywords SET word = ? WHERE id = ?", (new_word.strip(), keyword_id))
    return redirect('/')

@app.route('/search_pdf', methods=['POST'])
def search_pdf():
    file = request.files['pdf']
    pos_keywords = [word for _, word in get_keywords_by_type("positive")]
    neg_keywords = [word for _, word in get_keywords_by_type("negative")]

    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        results = []
        with fitz.open(filepath) as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                matches = []
                for keyword in pos_keywords + neg_keywords:
                    if keyword.lower() in text.lower():
                        count = text.lower().count(keyword.lower())
                        matches.append({
                            "keyword": keyword,
                            "type": "positive" if keyword in pos_keywords else "negative",
                            "count": count
                        })
                if matches:
                    results.append({
                        "page": page_num,
                        "matches": matches
                    })

        return render_template('index.html',
                               pos_keywords=get_keywords_by_type("positive"),
                               neg_keywords=get_keywords_by_type("negative"),
                               results=results)
    return redirect('/')
