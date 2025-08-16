import os
import re
import fitz  # PyMuPDF for PDFs
import pytesseract
from PIL import Image
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Example keyword lists
positive_keywords = ["approved", "success", "valid"]
negative_keywords = ["declined", "failed", "error"]

def extract_text_from_pdf(file_path):
    """Extract text per page from PDF using PyMuPDF."""
    text_pages = []
    doc = fitz.open(file_path)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        text_pages.append((page_num, text))
    return text_pages

def extract_text_from_image(file_path):
    """Extract text from an image using pytesseract."""
    img = Image.open(file_path)
    text = pytesseract.image_to_string(img)
    return [(1, text)]  # treat image as single-page

def highlight_snippet(snippet, word):
    """Highlight the keyword in the snippet using <mark> tags."""
    pattern = re.compile(re.escape(word), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", snippet)

def search_keywords(text_pages, keywords, keyword_type):
    """Search keywords in extracted text pages and return matches."""
    matches = []
    for page_num, text in text_pages:
        for word in keywords:
            pattern = re.compile(rf"(.{{0,30}}{word}.{{0,30}})", re.IGNORECASE)
            for snippet in pattern.findall(text):
                highlighted = highlight_snippet(snippet.strip(), word)
                matches.append({
                    "word": word,
                    "type": keyword_type,
                    "page": page_num,
                    "snippet": highlighted
                })
    return matches

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_files = request.files.getlist("files")
        results = []
        positive_count = 0
        negative_count = 0

        for file in uploaded_files:
            if file.filename == "":
                continue

            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            # Detect file type
            if filename.lower().endswith(".pdf"):
                text_pages = extract_text_from_pdf(file_path)
            else:
                text_pages = extract_text_from_image(file_path)

            # Search for keywords
            pos_matches = search_keywords(text_pages, positive_keywords, "positive")
            neg_matches = search_keywords(text_pages, negative_keywords, "negative")

            positive_count += len(pos_matches)
            negative_count += len(neg_matches)

            matches = pos_matches + neg_matches
            results.append({
                "filename": filename,
                "matches": matches
            })

        summary = {
            "positive": positive_count,
            "negative": negative_count,
            "total": positive_count + negative_count
        }

        return render_template("results.html", results=results, summary=summary)

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)
