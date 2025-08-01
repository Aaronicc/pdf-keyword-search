import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = "keywords.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT NOT NULL,
        type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
    )''')
    conn.commit()
    conn.close()


def get_keywords_by_type(keyword_type):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, word FROM keywords WHERE type = ?", (keyword_type,))
    keywords = c.fetchall()
    conn.close()
    return keywords


def add_keyword(word, keyword_type):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (word, keyword_type))
    conn.commit()
    conn.close()


def delete_keyword(keyword_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
    conn.commit()
    conn.close()


def update_keyword(keyword_id, new_word):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE keywords SET word = ? WHERE id = ?", (new_word, keyword_id))
    conn.commit()
    conn.close()


def extract_text_and_matches(pdf_path, pos_keywords, neg_keywords):
    matched_text = []
    full_text = ""

    doc = fitz.open(pdf_path)
    for page in doc:
        text = page.get_text()
        full_text += text
        for line in text.split('\n'):
            line_lower = line.lower()
            if any(word.lower() in line_lower for _, word in pos_keywords + neg_keywords):
                matched_text.append(line)
    return full_text, matched_text


@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    extracted_text = ""
    matched_lines = []

    if request.method == "POST":
        if "pdf_file" in request.files:
            pdf = request.files["pdf_file"]
            if pdf.filename.endswith(".pdf"):
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], pdf.filename)
                pdf.save(filepath)

                pos_keywords = get_keywords_by_type("positive")
                neg_keywords = get_keywords_by_type("negative")
                extracted_text, matched_lines = extract_text_and_matches(filepath, pos_keywords, neg_keywords)
                message = f"Found {len(matched_lines)} matching lines."
            else:
                message = "Please upload a valid PDF file."

    saved_pos_keywords = get_keywords_by_type("positive")
    saved_neg_keywords = get_keywords_by_type("negative")
    return render_template("index.html", message=message, extracted_text=extracted_text,
                           matched_lines=matched_lines,
                           pos_keywords=saved_pos_keywords,
                           neg_keywords=saved_neg_keywords)


@app.route("/add_keyword", methods=["POST"])
def add_keyword_route():
    word = request.form.get("word")
    keyword_type = request.form.get("type")
    if word and keyword_type in ["positive", "negative"]:
        add_keyword(word.strip(), keyword_type)
    return redirect(url_for("index"))


@app.route("/delete_keyword/<int:keyword_id>", methods=["POST"])
def delete_keyword_route(keyword_id):
    delete_keyword(keyword_id)
    return redirect(url_for("index"))


@app.route("/edit_keyword/<int:keyword_id>", methods=["POST"])
def edit_keyword_route(keyword_id):
    new_word = request.form.get("new_word")
    if new_word:
        update_keyword(keyword_id, new_word.strip())
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
