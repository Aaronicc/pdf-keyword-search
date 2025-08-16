import os
import re
from urllib.parse import urlparse

from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

import psycopg2
from psycopg2.extras import RealDictCursor

# -----------------------
# CONFIG
# -----------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-prod")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# One password for delete/edit actions
DELETE_EDIT_PASSWORD = os.environ.get("KEYWORD_ADMIN_PASSWORD", "1234")

ALLOWED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff")

# -----------------------
# DB Connection (Render/Local)
# -----------------------
def _conn_from_url(db_url: str):
    parsed = urlparse(db_url)
    return {
        "dbname": parsed.path.lstrip("/"),
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname,
        "port": parsed.port or 5432,
    }

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if DATABASE_URL:
    DB_PARAMS = _conn_from_url(DATABASE_URL)
else:
    DB_PARAMS = {
        "dbname": os.environ.get("POSTGRES_DB", "keywords_db"),
        "user": os.environ.get("POSTGRES_USER", "postgres"),
        "password": os.environ.get("POSTGRES_PASSWORD", "postgres"),
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": os.environ.get("POSTGRES_PORT", "5432"),
    }

def get_db_connection():
    return psycopg2.connect(**DB_PARAMS, cursor_factory=RealDictCursor)

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Store all keywords in lowercase for uniqueness; we still display as typed if you want later
    cur.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id SERIAL PRIMARY KEY,
            word TEXT NOT NULL,
            type TEXT CHECK(type IN ('positive','negative')) NOT NULL,
            CONSTRAINT keywords_word_unique UNIQUE (word)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

# Initialize at import so tables exist even before first request
try:
    init_db()
except Exception as e:
    # On cold boot before Postgres is ready, this may fail; it will be tried again on first request
    print("DB init skipped on import:", e)

# -----------------------
# Keyword helpers
# -----------------------
def get_keywords():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, word, type FROM keywords ORDER BY word;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    pos = [r["word"] for r in rows if r["type"] == "positive"]
    neg = [r["word"] for r in rows if r["type"] == "negative"]
    return pos, neg, rows

def add_keyword(word: str, ktype: str):
    word_lc = word.strip().lower()
    if not word_lc:
        return False, "Empty keyword."
    if ktype not in ("positive", "negative"):
        return False, "Invalid type."
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO keywords (word, type) VALUES (%s,%s)", (word_lc, ktype))
        conn.commit()
        return True, None
    except psycopg2.Error as e:
        conn.rollback()
        return False, "Duplicate or DB error."
    finally:
        cur.close()
        conn.close()

def delete_keyword(word: str, password: str):
    if password != DELETE_EDIT_PASSWORD:
        return False, "Wrong password."
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM keywords WHERE word=%s", (word.lower(),))
    conn.commit()
    cur.close()
    conn.close()
    return True, None

def edit_keyword(old_word: str, new_word: str, new_type: str, password: str):
    if password != DELETE_EDIT_PASSWORD:
        return False, "Wrong password."
    new_word_lc = new_word.strip().lower()
    if not new_word_lc or new_type not in ("positive", "negative"):
        return False, "Invalid input."
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE keywords SET word=%s, type=%s WHERE word=%s",
            (new_word_lc, new_type, old_word.lower())
        )
        if cur.rowcount == 0:
            conn.rollback()
            return False, "Keyword not found."
        conn.commit()
        return True, None
    except psycopg2.Error:
        conn.rollback()
        return False, "Duplicate or DB error."
    finally:
        cur.close()
        conn.close()

# -----------------------
# Snippet extraction
# -----------------------
def extract_snippets(text: str, pos_words, neg_words, context: int = 50):
    """
    Returns (snippets, counts) where:
      - snippets is a list of dicts { 'snippet': str, 'tag': 'positive'|'negative', 'keyword': str }
      - counts is a dict {'positive': int, 'negative': int, 'total': int}
    """
    snippets = []
    counts = {"positive": 0, "negative": 0, "total": 0}

    # Build keyword list; longer first to avoid nested overlaps in rendering
    all_keywords = sorted([(kw, "positive") for kw in pos_words] + [(kw, "negative") for kw in neg_words],
                          key=lambda x: len(x[0]),
                          reverse=True)

    for kw, ktype in all_keywords:
        if not kw:
            continue
        pattern = re.compile(re.escape(kw), re.IGNORECASE)
        for m in pattern.finditer(text):
            start = max(m.start() - context, 0)
            end = min(m.end() + context, len(text))
            snippet = text[start:end]
            # Highlight the exact matched span using a case-insensitive replacement
            snippet = re.sub(
                pattern,
                lambda _m: f"<mark class='{ktype}'>{_m.group(0)}</mark>",
                snippet
            )
            snippets.append({"snippet": snippet.strip(), "tag": ktype, "keyword": kw})
            counts[ktype] += 1
            counts["total"] += 1

    return snippets, counts

# -----------------------
# File processors
# -----------------------
def process_pdf(filepath: str, pos_words, neg_words, context: int = 50):
    results = []
    doc = fitz.open(filepath)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        snippets, counts = extract_snippets(text, pos_words, neg_words, context=context)
        for s in snippets:
            results.append({
                "filename": os.path.basename(filepath),
                "page": page_num,
                "snippet": s["snippet"],
                "tag": s["tag"],
                "keyword": s["keyword"]
            })
    return results

def process_image(filepath: str, pos_words, neg_words, context: int = 50):
    img = Image.open(filepath)
    text = pytesseract.image_to_string(img) or ""
    snippets, counts = extract_snippets(text, pos_words, neg_words, context=context)
    return [
        {
            "filename": os.path.basename(filepath),
            "page": 1,
            "snippet": s["snippet"],
            "tag": s["tag"],
            "keyword": s["keyword"]
        }
        for s in snippets
    ]

# -----------------------
# Routes
# -----------------------
@app.before_request
def ensure_db_ready():
    # In case the earlier init failed during cold start
    try:
        init_db()
    except Exception:
        pass

@app.route("/", methods=["GET", "POST"])
def index():
    pos, neg, rows = get_keywords()

    results = []
    summary = {"positive": 0, "negative": 0, "total": 0}

    if request.method == "POST":
        files = request.files.getlist("files")
        context = int(request.form.get("context", 50) or 50)

        for file in files:
            if not file or not file.filename:
                continue

            filename = secure_filename(file.filename)
            # Avoid accidental overwrite: add a counter if file exists
            base, ext = os.path.splitext(filename)
            i = 1
            savepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            while os.path.exists(savepath):
                filename = f"{base}_{i}{ext}"
                savepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                i += 1

            file.save(savepath)

            lower = filename.lower()
            if lower.endswith(".pdf"):
                res = process_pdf(savepath, pos, neg, context=context)
            elif lower.endswith(ALLOWED_IMAGE_EXTS):
                res = process_image(savepath, pos, neg, context=context)
            else:
                flash(f"Unsupported file type: {filename}")
                continue

            # accumulate
            results.extend(res)

        # Build summary counts from results
        for r in results:
            if r["tag"] == "positive":
                summary["positive"] += 1
            elif r["tag"] == "negative":
                summary["negative"] += 1
        summary["total"] = summary["positive"] + summary["negative"]

    return render_template(
        "index.html",
        results=results,
        summary=summary,
        keywords=rows,
        admin_password_set=bool(os.environ.get("KEYWORD_ADMIN_PASSWORD")),
    )

@app.route("/add_keyword", methods=["POST"])
def add_kw():
    word = (request.form.get("word") or "").strip()
    ktype = request.form.get("type")
    ok, msg = add_keyword(word, ktype)
    if not ok and msg:
        flash(msg)
    return redirect(url_for("index"))

@app.route("/delete_keyword", methods=["POST"])
def del_kw():
    word = request.form.get("word") or ""
    password = request.form.get("password") or ""
    ok, msg = delete_keyword(word, password)
    if not ok and msg:
        flash(msg)
    return redirect(url_for("index"))

@app.route("/edit_keyword", methods=["POST"])
def edit_kw():
    old_word = request.form.get("old_word") or ""
    new_word = request.form.get("new_word") or ""
    new_type = request.form.get("new_type") or ""
    password = request.form.get("password") or ""
    ok, msg = edit_keyword(old_word, new_word, new_type, password)
    if not ok and msg:
        flash(msg)
    return redirect(url_for("index"))

# -----------------------
# Entrypoint (local dev)
# -----------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
