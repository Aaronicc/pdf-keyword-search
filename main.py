import re
from flask import Flask, render_template, request
import os
import PyPDF2

app = Flask(__name__)

SAVED_KEYWORDS_FILE = "saved_keywords.txt"

def extract_lines_with_keywords(pdf_path, keywords):
    results = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.splitlines()
            for line in lines:
                for keyword in keywords:
                    if keyword.lower() in line.lower():
                        # Optionally extract date too
                        date_match = re.search(r"\d{2} [A-Za-z]{3} \d{2}", line)
                        date_str = date_match.group() if date_match else "No Date Found"
                        results.append(f"Page {page_num + 1} | Date: {date_str} | Line: {line.strip()}")
                        break  # Avoid duplicate keyword matches in same line
    return results

def load_saved_keywords():
    if os.path.exists(SAVED_KEYWORDS_FILE):
        with open(SAVED_KEYWORDS_FILE, "r") as f:
            return [kw.strip() for kw in f.read().split(",") if kw.strip()]
    return []

def save_keywords(new_keywords):
    existing = set(load_saved_keywords())
    updated = existing.union(set(new_keywords))
    with open(SAVED_KEYWORDS_FILE, "w") as f:
        f.write(",".join(sorted(updated)))

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    saved_keywords = load_saved_keywords()
    if request.method == "POST":
        uploaded_file = request.files.get("pdf")
        keywords_input = request.form.get("keywords", "")
        keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]

        if uploaded_file and keywords:
            pdf_path = os.path.join("uploads", uploaded_file.filename)
            os.makedirs("uploads", exist_ok=True)
            uploaded_file.save(pdf_path)

            results = extract_lines_with_keywords(pdf_path, keywords)
            save_keywords(keywords)

    return render_template("index.html", results=results, saved_keywords=saved_keywords)
