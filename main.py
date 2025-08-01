import os
import fitz  # PyMuPDF
import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_NAME = "keywords.db"


# ---------- DATABASE SETUP ----------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def add_keywords_to_db(keywords, keyword_type):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    for word in keywords:
        c.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (word.strip(), keyword_type))
    conn.commit()
    conn.close()


def get_keywords_by_type(keyword_type):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT word FROM keywords WHERE type = ?", (keyword_type,))
    keywords = [row[0] for row in c.fetchall()]
    conn.close()
    return keywords


# ---------- PDF KEYWORD MATCH ----------
def extract_keyword_matches(pdf_path, keywords):
    results = []
    keyword_counts = {kw.lower(): 0 for kw in keywords}

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc):
            lines = page.get_text("text").split('\n')
            for line in lines:
                for keyword in keywords:
                    if keyword.lower() in line.lower():
                        keyword_counts[keyword.lower()] += 1
                        # Highlight in the result line
                        highlighted_line = line
                        for kw in keywords:
                            highlighted_line = highlighted_line.replace(
                                kw, f"<span class='match-highlight'>{kw}</span>"
                            )
                            highlighted_line = highlighted_line.replace(
                                kw.upper(), f"<span class='match-highlight'>{kw.upper()}</span>"
                            )
                            highlighted_line = highlighted_line.replace(
                                kw.lower(), f"<span class='match-highlight'>{kw.lower()}</span>"
                            )
                        results.append(
                            f"✅ Page {page_num + 1} | 🔍 Matched: '{keyword}' | 💬 Line: {highlighted_line.strip()}"
                        )
    return results, keyword_counts


# ---------- ROUTES ----------
@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    counts = {}
    saved_pos_keywords = get_keywords_by_type("positive")
    saved_neg_keywords = get_keywords_by_type("negative")

    if request.method == "POST":
        uploaded_file = request.files.get("pdf_file")
        keywords_text = request.form.get("keywords", "")
        keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]

        if uploaded_file and uploaded_file.filename.endswith(".pdf"):
            filename = secure_filename(uploaded_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(filepath)

            try:
                results, counts = extract_keyword_matches(filepath, keywords)
            except Exception as e:
                results = [f"❌ Error reading PDF: {str(e)}"]

    return render_template(
        "index.html",
        results=results,
        counts=counts,
        saved_pos_keywords=saved_pos_keywords,
        saved_neg_keywords=saved_neg_keywords
    )


@app.route("/add_keywords", methods=["POST"])
def add_keywords():
    pos_keywords_text = request.form.get("positive_keywords", "")
    neg_keywords_text = request.form.get("negative_keywords", "")

    pos_keywords = [kw.strip() for kw in pos_keywords_text.split(",") if kw.strip()]
    neg_keywords = [kw.strip() for kw in neg_keywords_text.split(",") if kw.strip()]

    if pos_keywords:
        add_keywords_to_db(pos_keywords, "positive")
    if neg_keywords:
        add_keywords_to_db(neg_keywords, "negative")

    return redirect(url_for("index"))


# ---------- MAIN ----------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
