import os
import fitz  # PyMuPDF
import sqlite3
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Setup database ---
DB_PATH = "keywords.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL,
                    type TEXT CHECK(type IN ('positive','negative')) NOT NULL
                 )''')
    conn.commit()
    conn.close()

def save_keywords(words, keyword_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for word in words:
        c.execute("INSERT INTO keywords (word, type) VALUES (?, ?)", (word.lower(), keyword_type))
    conn.commit()
    conn.close()

def get_keywords_by_type(keyword_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT word FROM keywords WHERE type = ?", (keyword_type,))
    results = [row[0] for row in c.fetchall()]
    conn.close()
    return sorted(set(results))

# --- PDF processing ---
def extract_keyword_matches(pdf_path, positive_keywords, negative_keywords):
    results = []
    keyword_counts = {kw: 0 for kw in positive_keywords}

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc):
            lines = page.get_text("text").split('\n')
            for line in lines:
                line_lower = line.lower()
                if any(nk in line_lower for nk in negative_keywords):
                    continue
                for keyword in positive_keywords:
                    if keyword in line_lower:
                        keyword_counts[keyword] += 1
                        highlighted = line
                        for kw in positive_keywords:
                            highlighted = highlighted.replace(kw, f"**{kw}**")
                        results.append(
                            f"✅ Page {page_num + 1} | 🔍 Matched: '{keyword}' | 💬 Line: {highlighted.strip()}"
                        )
    return results, keyword_counts

# --- Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    counts = {}
    positive_keywords = []
    negative_keywords = []

    if request.method == "POST":
        uploaded_file = request.files["pdf_file"]
        pos_input = request.form.get("positive_keywords", "")
        neg_input = request.form.get("negative_keywords", "")
        positive_keywords = [kw.strip().lower() for kw in pos_input.split(",") if kw.strip()]
        negative_keywords = [kw.strip().lower() for kw in neg_input.split(",") if kw.strip()]

        if request.form.get("save_keywords"):
            save_keywords(positive_keywords, "positive")
            save_keywords(negative_keywords, "negative")

        if uploaded_file and uploaded_file.filename.endswith(".pdf"):
            filename = secure_filename(uploaded_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(filepath)
            try:
                results, counts = extract_keyword_matches(filepath, positive_keywords, negative_keywords)
            except Exception as e:
                results = [f"❌ Error reading PDF: {str(e)}"]

    # Load saved keywords for reuse
    saved_pos_keywords = get_keywords_by_type("positive")
    saved_neg_keywords = get_keywords_by_type("negative")

    return render_template("index.html",
                           results=results,
                           counts=counts,
                           saved_pos_keywords=saved_pos_keywords,
                           saved_neg_keywords=saved_neg_keywords)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
