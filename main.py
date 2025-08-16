from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import psycopg2
from psycopg2.extras import RealDictCursor

# -----------------------
# CONFIG
# -----------------------
app = Flask(__name__)
app.secret_key = "super-secret-key"  # change this in prod

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DB_PARAMS = {
    "dbname": os.environ.get("POSTGRES_DB", "keywords_db"),
    "user": os.environ.get("POSTGRES_USER", "postgres"),
    "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
    "host": os.environ.get("POSTGRES_HOST", "localhost"),
    "port": os.environ.get("POSTGRES_PORT", "5432"),
}

DELETE_PASSWORD = "1234"  # change this to your own password


# -----------------------
# DB Helpers
# -----------------------
def get_db_connection():
    return psycopg2.connect(**DB_PARAMS, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id SERIAL PRIMARY KEY,
            word TEXT UNIQUE NOT NULL,
            type TEXT CHECK(type IN ('positive','negative')) NOT NULL
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def get_keywords():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM keywords ORDER BY word;")
    rows = cur.fetchall()
    conn.close()
    pos = [r["word"] for r in rows if r["type"] == "positive"]
    neg = [r["word"] for r in rows if r["type"] == "negative"]
    return pos, neg

def add_keyword(word, ktype):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO keywords (word, type) VALUES (%s,%s)", (word, ktype))
        conn.commit()
    except psycopg2.Error:
        pass  # duplicate
    finally:
        cur.close()
        conn.close()

def delete_keyword(word, password):
    if password != DELETE_PASSWORD:
        return False
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM keywords WHERE word=%s", (word,))
    conn.commit()
    cur.close()
    conn.close()
    return True


# -----------------------
# Text Highlight
# -----------------------
def highlight_text(text, keywords, css_class):
    for kw in keywords:
        text = text.replace(kw, f"<mark class='{css_class}'>{kw}</mark>")
    return text

def process_pdf(filepath, pos, neg):
    results = []
    doc = fitz.open(filepath)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        highlighted = highlight_text(text, pos, "positive")
        highlighted = highlight_text(highlighted, neg, "negative")
        results.append({"filename": os.path.basename(filepath), "page": page_num, "text": highlighted})
    return results

def process_image(filepath, pos, neg):
    img = Image.open(filepath)
    text = pytesseract.image_to_string(img)
    highlighted = highlight_text(text, pos, "positive")
    highlighted = highlight_text(highlighted, neg, "negative")
    return [{"filename": os.path.basename(filepath), "page": 1, "text": highlighted}]


# -----------------------
# Routes
# -----------------------
@app.route("/", methods=["GET", "POST"])
def index():
    pos, neg = get_keywords()
    results = []
    if request.method == "POST":
        files = request.files.getlist("files")
        for file in files:
            if not file:
                continue
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            if filename.lower().endswith(".pdf"):
                results.extend(process_pdf(filepath, pos, neg))
            elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
                results.extend(process_image(filepath, pos, neg))
    return render_template("index.html", results=results, pos=pos, neg=neg)

@app.route("/add_keyword", methods=["POST"])
def add_kw():
    word = request.form.get("word").strip()
    ktype = request.form.get("type")
    if word and ktype:
        add_keyword(word, ktype)
    return redirect(url_for("index"))

@app.route("/delete_keyword", methods=["POST"])
def del_kw():
    word = request.form.get("word")
    password = request.form.get("password")
    if not delete_keyword(word, password):
        flash("Wrong password for deletion!")
    return redirect(url_for("index"))


# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
