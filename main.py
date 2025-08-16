import os
import fitz  # PyMuPDF for PDFs
import pytesseract
from PIL import Image
from flask import Flask, request, render_template, redirect, url_for, jsonify
import psycopg

app = Flask(__name__)

# ✅ PostgreSQL Connection
DATABASE_URL = os.getenv("DATABASE_URL")
def get_conn():
    return psycopg.connect(DATABASE_URL, autocommit=True)

# ✅ Initialize database
with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id SERIAL PRIMARY KEY,
                word TEXT UNIQUE NOT NULL,
                type TEXT CHECK(type IN ('positive','negative')) NOT NULL
            )
        """)

# ✅ Extract text from PDF
def extract_text_from_pdf(file_path):
    text_content = []
    with fitz.open(file_path) as pdf:
        for page_num, page in enumerate(pdf, start=1):
            text = page.get_text("text")
            if text.strip():
                text_content.append((page_num, text))
    return text_content

# ✅ Extract text from Image (OCR)
def extract_text_from_image(file_path):
    img = Image.open(file_path)
    text = pytesseract.image_to_string(img)
    return [(1, text)]  # Treat as single-page

# ✅ Home Page
@app.route("/")
def index():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, word, type FROM keywords ORDER BY id")
            keywords = cur.fetchall()
    return render_template("index.html", keywords=keywords)

# ✅ Upload & Search
@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("files")
    results = []

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT word, type FROM keywords")
            keywords = cur.fetchall()

    for f in files:
        file_path = os.path.join("uploads", f.filename)
        os.makedirs("uploads", exist_ok=True)
        f.save(file_path)

        if f.filename.lower().endswith(".pdf"):
            extracted = extract_text_from_pdf(file_path)
        else:
            extracted = extract_text_from_image(file_path)

        file_results = {"filename": f.filename, "matches": []}
        for page_num, text in extracted:
            for word, ktype in keywords:
                if word.lower() in text.lower():
                    snippet_start = max(text.lower().find(word.lower()) - 30, 0)
                    snippet_end = snippet_start + 100
                    snippet = text[snippet_start:snippet_end]
                    file_results["matches"].append({
                        "word": word,
                        "type": ktype,
                        "page": page_num,
                        "snippet": snippet
                    })
        results.append(file_results)

    return render_template("results.html", results=results)

# ✅ Add Keyword
@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form["word"].strip()
    ktype = request.form["type"]

    with get_conn() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("INSERT INTO keywords (word, type) VALUES (%s, %s)", (word, ktype))
            except psycopg.errors.UniqueViolation:
                return jsonify({"error": "Keyword already exists"}), 400

    return redirect(url_for("index"))

# ✅ Delete Keyword (password protected)
@app.route("/delete_keyword/<int:keyword_id>", methods=["POST"])
def delete_keyword(keyword_id):
    password = request.form.get("password")
    if password != os.getenv("DELETE_PASSWORD", "secret123"):  # default password
        return jsonify({"error": "Invalid password"}), 403

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM keywords WHERE id = %s", (keyword_id,))
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
