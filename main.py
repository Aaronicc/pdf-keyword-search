from flask import Flask, request, render_template
import os
import PyPDF2
import re
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

previous_keywords = []

def extract_lines_with_keywords(pdf_path, keywords):
    results = []
    keyword_counts = {kw.lower(): 0 for kw in keywords}

    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        lines = text.split("\n")
                        for line in lines:
                            for keyword in keywords:
                                if keyword.lower() in line.lower():
                                    # Find date in the line if any (format: DD MMM YY or D MMM YY)
                                    match_date = re.search(r'\b\d{1,2} [A-Za-z]{3} \d{2}\b', line)
                                    date_found = match_date.group(0) if match_date else "N/A"
                                    keyword_counts[keyword.lower()] += 1
                                    # Highlight keyword
                                    highlighted_line = re.sub(f"(?i)({re.escape(keyword)})", r"<mark>\1</mark>", line)
                                    results.append(f"✅ Page {page_num+1} | 📅 Date: {date_found} | 🔍 Matched: '{keyword}' | 💬 Line: {highlighted_line}")
                                    break
                except Exception as e:
                    results.append(f"❌ Error reading page {page_num+1}: {str(e)}")
    except Exception as e:
        results.append(f"❌ Failed to read PDF: {str(e)}")

    total_matches = sum(keyword_counts.values())
    return results, {"total_matches": total_matches, "keyword_counts": keyword_counts}

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    summary = None

    if request.method == "POST":
        keywords = request.form.get("keywords", "").split(",")
        keywords = [k.strip() for k in keywords if k.strip()]

        # Add previously selected checkboxes
        keywords += request.form.getlist("previous_keywords")
        keywords = list(set(k.lower() for k in keywords))  # unique, lowercase

        if keywords:
            for kw in keywords:
                if kw not in previous_keywords:
                    previous_keywords.append(kw)

        uploaded_file = request.files.get("pdf_file")
        if uploaded_file:
            filename = uploaded_file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            uploaded_file.save(filepath)
            results, summary = extract_lines_with_keywords(filepath, keywords)

    return render_template(
        "index.html",
        results=results,
        previous_keywords=previous_keywords,
        summary=summary
    )

if __name__ == "__main__":
    app.run(debug=True)
