import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = 'keywords.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('positive', 'negative'))
    )''')
    conn.commit()
    conn.close()

init_db()

def add_keyword(word, keyword_type):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (word, keyword_type))
    conn.commit()
    conn.close()

def get_keywords_by_type(keyword_type):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, word FROM keywords WHERE type = ?", (keyword_type,))
    keywords = c.fetchall()
    conn.close()
    return keywords

def update_keyword(keyword_id, new_word):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE keywords SET word = ? WHERE id = ?", (new_word, keyword_id))
    conn.commit()
    conn.close()

def delete_keyword(keyword_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
    conn.commit()
    conn.close()

def extract_text_and_highlight(pdf_path, keywords):
    text_output = ""
    highlights = []

    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc):
        text = page.get_text()
        text_output += f"\n--- Page {page_num + 1} ---\n{text}"
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text.lower():
                highlights.append(kw)
    return text_output, set(highlights)

@app.route("/", methods=["GET", "POST"])
def index():
    result_text = ""
    matched_keywords = []

    if request.method == "POST" and "pdf_file" in request.files:
        pdf_file = request.files["pdf_file"]
        if pdf_file.filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
            pdf_file.save(filepath)

            pos_keywords = [kw[1] for kw in get_keywords_by_type("positive")]
            neg_keywords = [kw[1] for kw in get_keywords_by_type("negative")]
            all_keywords = pos_keywords + neg_keywords

            result_text, matched_keywords = extract_text_and_highlight(filepath, all_keywords)

    saved_pos_keywords = get_keywords_by_type("positive")
    saved_neg_keywords = get_keywords_by_type("negative")

    return render_template("index.html",
                           result_text=result_text,
                           matched_keywords=matched_keywords,
                           pos_keywords=saved_pos_keywords,
                           neg_keywords=saved_neg_keywords)

@app.route("/add_keyword", methods=["POST"])
def add_keyword_route():
    word = request.form.get("word", "").strip()
    keyword_type = request.form.get("type", "").strip()
    if word and keyword_type in ["positive", "negative"]:
        add_keyword(word, keyword_type)
    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:keyword_id>", methods=["POST"])
def delete_keyword_route(keyword_id):
    delete_keyword(keyword_id)
    return redirect(url_for("index"))

@app.route("/edit_keyword/<int:keyword_id>", methods=["POST"])
def edit_keyword_route(keyword_id):
    new_word = request.form.get("new_word", "").strip()
    if new_word:
        update_keyword(keyword_id, new_word)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
