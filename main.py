import os
import re
import io
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy

# PDF text extraction
import fitz  # PyMuPDF

# Image OCR
from PIL import Image
import pytesseract

# ---------------------------
# App & Config
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Where uploads are stored (absolute path)
UPLOAD_ROOT = os.path.join(BASE_DIR, 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_ROOT

# Ensure uploads folder exists (no crash if already there)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ---------------------------
# Database Models
# ---------------------------
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(256), unique=True, nullable=False)

    def __repr__(self):
        return f"<Keyword {self.word!r}>"

# Create tables at startup
with app.app_context():
    db.create_all()

# ---------------------------
# Helpers
# ---------------------------
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tif', 'tiff'}

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def normalize(s: str) -> str:
    """Simple casefold normalize for robust matching."""
    return s.casefold()

def highlight_text_html(text: str, keywords: list[str]) -> str:
    """
    Wrap keyword matches with <mark>…</mark>.
    Uses case-insensitive, whole-or-substring match (safe HTML escaping via Jinja).
    """
    if not text or not keywords:
        return text or ""

    # Build one regex that ORs all keywords; escape to treat them literally
    escaped = [re.escape(k) for k in keywords if k.strip()]
    if not escaped:
        return text

    pattern = re.compile(r'(' + '|'.join(escaped) + r')', re.IGNORECASE)

    # Replace with <mark>…</mark>
    return pattern.sub(r'<mark>\1</mark>', text)

def extract_pdf_matches(filepath: str, keywords: list[str]) -> list[dict]:
    """
    Read PDF text page-by-page and find keyword occurrences.
    Returns list of {keyword, page, snippet}.
    """
    results = []
    if not keywords:
        return results

    lowered = [normalize(k) for k in keywords if k.strip()]
    if not lowered:
        return results

    try:
        with fitz.open(filepath) as doc:
            for page_index, page in enumerate(doc, start=1):
                text = page.get_text() or ""
                low_text = normalize(text)
                for k_raw, k in zip(keywords, lowered):
                    pos = 0
                    while True:
                        found = low_text.find(k, pos)
                        if found == -1:
                            break
                        start = max(0, found - 60)
                        end = min(len(text), found + len(k) + 60)
                        snippet = text[start:end].replace('\n', ' ')
                        results.append({
                            "keyword": k_raw,
                            "page": page_index,
                            "snippet": snippet
                        })
                        pos = found + len(k)
    except Exception as e:
        results.append({
            "error": f"PDF parse error: {e}"
        })

    return results

def ocr_image_with_boxes(filepath: str) -> tuple[str, list[dict], dict]:
    """
    OCR an image file and return:
      - full_text (string),
      - boxes: [{word, x, y, w, h}], in pixel coords,
      - natural_size: {'width': int, 'height': int}

    Uses pytesseract.image_to_data to get word-level boxes.
    """
    try:
        img = Image.open(filepath).convert("RGB")
    except Exception as e:
        return f"Image open error: {e}", [], {"width": 0, "height": 0}

    natural_size = {"width": img.width, "height": img.height}
    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except pytesseract.TesseractNotFoundError:
        return (
            "Tesseract OCR binary not found. Install it or provide TESSERACT_CMD path.",
            [], natural_size
        )
    except Exception as e:
        return (f"OCR error: {e}", [], natural_size)

    words = data.get("text", [])
    lefts = data.get("left", [])
    tops = data.get("top", [])
    widths = data.get("width", [])
    heights = data.get("height", [])

    full_text = " ".join([w for w in words if (w or "").strip()])
    boxes = []
    for i, w in enumerate(words):
        w_clean = (w or "").strip()
        if not w_clean:
            continue
        boxes.append({
            "word": w_clean,
            "x": int(lefts[i]),
            "y": int(tops[i]),
            "w": int(widths[i]),
            "h": int(heights[i]),
        })
    return full_text, boxes, natural_size

def filter_boxes_for_keywords(boxes: list[dict], keywords: list[str]) -> list[dict]:
    """Return only boxes whose 'word' contains any keyword (case-insensitive)."""
    targets = [normalize(k) for k in keywords if k.strip()]
    if not targets:
        return []
    hits = []
    for b in boxes:
        w = normalize(b.get("word", ""))
        if any(t in w for t in targets):
            hits.append(b)
    return hits

# ---------------------------
# Routes
# ---------------------------
@app.route('/', methods=['GET'])
def index():
    all_keywords = [k.word for k in Keyword.query.order_by(Keyword.word.asc()).all()]
    return render_template('index.html',
                           keywords=all_keywords,
                           results=None,
                           uploaded_image=None,
                           natural_size=None)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    word = (request.form.get('keyword') or '').strip()
    if not word:
        flash("Keyword cannot be empty.", "warning")
        return redirect(url_for('index'))

    exists = Keyword.query.filter(
        db.func.lower(Keyword.word) == word.lower()
    ).first()
    if exists:
        flash(f"'{word}' already exists.", "info")
        return redirect(url_for('index'))

    db.session.add(Keyword(word=word))
    db.session.commit()
    flash(f"Added keyword: {word}", "success")
    return redirect(url_for('index'))

@app.route('/delete_keyword/<int:id>', methods=['POST'])
def delete_keyword(id):
    kw = Keyword.query.get_or_404(id)
    db.session.delete(kw)
    db.session.commit()
    flash(f"Deleted keyword: {kw.word}", "success")
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part in request.', 'danger')
        return redirect(url_for('index'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file.', 'warning')
        return redirect(url_for('index'))

    if not allowed_file(file.filename):
        flash('Unsupported file type.', 'danger')
        return redirect(url_for('index'))

    # Save file
    fname = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}_{file.filename}"
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
    file.save(save_path)

    # Keywords list (strings)
    keywords = [k.word for k in Keyword.query.order_by(Keyword.word.asc()).all()]

    ext = file.filename.rsplit('.', 1)[1].lower()

    # Prepare results payload for template
    results = {
        "type": None,  # 'pdf' or 'image'
        "pdf_matches": [],
        "image_text_html": "",
        "image_boxes": [],
        "image_hit_boxes": [],
        "message": ""
    }
    uploaded_image_rel = None
    natural_size = None

    if ext == 'pdf':
        results["type"] = "pdf"
        results["pdf_matches"] = extract_pdf_matches(save_path, keywords)
        if not results["pdf_matches"]:
            results["message"] = "No matches found in PDF."
    else:
        # Image flow
        results["type"] = "image"
        full_text, boxes, natural_size = ocr_image_with_boxes(save_path)

        # Highlighted plain text
        results["image_text_html"] = highlight_text_html(full_text, keywords)
        results["image_boxes"] = boxes
        results["image_hit_boxes"] = filter_boxes_for_keywords(boxes, keywords)

        # make the file accessible to template
        uploaded_image_rel = fname

        if not full_text.strip():
            results["message"] = "No text detected in image."

        if not results["image_hit_boxes"] and full_text.strip():
            results["message"] = "No keyword matches found in image text."

    # Render with results
    all_keywords = [k.word for k in Keyword.query.order_by(Keyword.word.asc()).all()]
    return render_template('index.html',
                           keywords=all_keywords,
                           results=results,
                           uploaded_image=uploaded_image_rel,
                           natural_size=natural_size)

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    # Serve uploaded files
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------------------
# Entrypoint (for local dev)
# ---------------------------
if __name__ == '__main__':
    # For local testing
    app.run(host='0.0.0.0', port=5000, debug=True)
