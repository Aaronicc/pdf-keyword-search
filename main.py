import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'keywords.db'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def init_db():
    with sqlite3.connect(app.config['DATABASE']) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL,
                type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
            )
        ''')
        conn.commit()


def get_keywords_by_type(keyword_type):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        c = conn.cursor()
        c.execute("SELECT id, word FROM keywords WHERE type = ?", (keyword_type,))
        return c.fetchall()


def save_keyword_to_db(word, keyword_type):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (word, keyword_type))
        conn.commit()


def delete_keyword_from_db(keyword_id):
    with sqlite3.connect(app.config['DATABASE']) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
        conn.commit()


def extract_keyword_matches(pdf_path, keywords):
    results = []
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc):
        text = page.get_text()
        for kw in keywords:
            if kw.lower() in text.lower():
                results.append((kw, page_num + 1))  # Page numbers are 1-based
    return results


@app.route("/", methods=["GET"])
def index():
    saved_pos_keywords = get_keywords_by_type("positive")
    saved_neg_keywords = get_keywords_by_type("negative")
    return render_template("index.html", pos_keywords=saved_pos_keywords, neg_keywords=saved_neg_keywords)


@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    keyword = request.form["keyword"].strip()
    keyword_type = request.form["keyword_type"]
    if keyword:
        save_keyword_to_db(keyword, keyword_type)
    return redirect(url_for("index"))


@app.route("/delete_keyword/<int:keyword_id>", methods=["POST"])
def delete_keyword(keyword_id):
    delete_keyword_from_db(keyword_id)
    return redirect(url_for("index"))


@app.route("/search_pdf", methods=["POST"])
def search_pdf():
    file = request.files['pdf_file']
    if not file:
        return "No file uploaded"

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    pos_keywords = [kw[1] for kw in get_keywords_by_type("positive")]
    neg_keywords = [kw[1] for kw in get_keywords_by_type("negative")]

    pos_matches = extract_keyword_matches(filepath, pos_keywords)
    neg_matches = extract_keyword_matches(filepath, neg_keywords)

    return render_template("index.html",
                           pos_keywords=get_keywords_by_type("positive"),
                           neg_keywords=get_keywords_by_type("negative"),
                           pos_matches=pos_matches,
                           neg_matches=neg_matches)


if __name__ != "__main__":
    init_db()
