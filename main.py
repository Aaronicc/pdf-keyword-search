import os
import fitz  # PyMuPDF for PDF text extraction
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import pytesseract

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

# Example keyword storage (later can be PostgreSQL)
positive_keywords = ["approved", "verified", "valid"]
negative_keywords = ["rejected", "fraud", "invalid"]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(filepath):
    """Extract text from PDF with page numbers."""
    text_by_page = []
    with fitz.open(filepath) as pdf:
        for page_num, page in enumerate(pdf, start=1):
            text = page.get_text("text")
            text_by_page.append((page_num, text))
    return text_by_page


def extract_text_from_image(filepath):
    """Extract text from image using OCR."""
    img = Image.open(filepath)
    text = pytesseract.image_to_string(img)
    return [(None, text)]  # keep consistent with PDF format


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if "files" not in request.files:
            return redirect(request.url)

        files = request.files.getlist("files")
        results = {}

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(filepath)

                # Extract text depending on file type
                if filename.lower().endswith(".pdf"):
                    texts = extract_text_from_pdf(filepath)
                else:
                    texts = extract_text_from_image(filepath)

                matches = []
                for page_num, text in texts:
                    for keyword in positive_keywords + negative_keywords:
                        if keyword.lower() in text.lower():
                            snippet_start = text.lower().find(keyword.lower()) - 30
                            snippet_end = snippet_start + len(keyword) + 60
                            snippet_start = max(0, snippet_start)
                            snippet_end = min(len(text), snippet_end)
                            snippet = text[snippet_start:snippet_end]
                            snippet = snippet.replace(
                                keyword, f"<mark>{keyword}</mark>"
                            )

                            matches.append({
                                "keyword": keyword,
                                "type": "positive" if keyword in positive_keywords else "negative",
                                "page": page_num,
                                "snippet": snippet
                            })

                results[filename] = matches

        return render_template("results.html", results=results)

    return render_template("index.html")


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)
