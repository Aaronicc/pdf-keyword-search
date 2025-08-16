from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF for PDFs
from PIL import Image
import pytesseract

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Example keyword storage (replace with DB)
positive_keywords = ["approved", "verified", "confirmed"]
negative_keywords = ["rejected", "fraud", "declined"]

def highlight_text(text, keywords, css_class):
    for kw in keywords:
        text = text.replace(kw, f"<mark class='{css_class}'>{kw}</mark>")
    return text

def process_pdf(filepath):
    """Extract text per page from PDF and highlight keywords."""
    results = []
    doc = fitz.open(filepath)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        highlighted = highlight_text(text, positive_keywords, "positive")
        highlighted = highlight_text(highlighted, negative_keywords, "negative")
        results.append({
            "filename": os.path.basename(filepath),
            "page": page_num,
            "text": highlighted
        })
    return results

def process_image(filepath):
    """Extract text from image using OCR and highlight keywords."""
    img = Image.open(filepath)
    text = pytesseract.image_to_string(img)
    highlighted = highlight_text(text, positive_keywords, "positive")
    highlighted = highlight_text(highlighted, negative_keywords, "negative")
    return [{
        "filename": os.path.basename(filepath),
        "page": 1,
        "text": highlighted
    }]

@app.route("/", methods=["GET", "POST"])
def index():
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
                results.extend(process_pdf(filepath))
            elif filename.lower().endswith((".png", ".jpg", ".jpeg")):
                results.extend(process_image(filepath))
    return render_template("index.html", results=results)

if __name__ == "__main__":
    app.run(debug=True)
