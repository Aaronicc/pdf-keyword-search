import os
import fitz  # PyMuPDF
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

keyword_history = set()
negative_keyword_history = set()

def extract_keyword_matches(pdf_path, keywords, negative_keywords):
    results = []
    keyword_counts = {kw.lower(): 0 for kw in keywords}
    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc):
            lines = page.get_text("text").split('\n')
            for line in lines:
                line_lower = line.lower()
                if any(neg.lower() in line_lower for neg in negative_keywords):
                    continue  # skip lines with negative keywords
                matched = [kw for kw in keywords if kw.lower() in line_lower]
                if matched:
                    for kw in matched:
                        keyword_counts[kw.lower()] += 1
                    highlighted_line = line
                    for kw in keywords:
                        highlighted_line = highlighted_line.replace(
                            kw, f"<mark>{kw}</mark>")
                        highlighted_line = highlighted_line.replace(
                            kw.upper(), f"<mark>{kw.upper()}</mark>")
                        highlighted_line = highlighted_line.replace(
                            kw.lower(), f"<mark>{kw.lower()}</mark>")
                    results.append(
                        f"✅ Page {page_num + 1} | 🔍 Matched: '{matched[0]}' | 💬 Line: {highlighted_line.strip()}")
    return results, keyword_counts

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    counts = {}
    keywords = []
    negative_keywords = []

    if request.method == "POST":
        uploaded_file = request.files["pdf_file"]

        # New keyword input from text box
        keywords_text = request.form.get("keywords", "")
        negative_keywords_text = request.form.get("negative_keywords", "")

        new_keywords = [kw.strip() for kw in keywords_text.split(",") if kw.strip()]
        new_negative_keywords = [kw.strip() for kw in negative_keywords_text.split(",") if kw.strip()]

        # Checkbox selections
        saved_keywords = request.form.getlist("saved_keywords")
        saved_negative_keywords = request.form.getlist("saved_negative_keywords")

        # Combine and deduplicate
        keywords = list(set(new_keywords + saved_keywords))
        negative_keywords = list(set(new_negative_keywords + saved_negative_keywords))

        keyword_history.update(new_keywords)
        negative_keyword_history.update(new_negative_keywords)

        if uploaded_file and uploaded_file.filename.endswith(".pdf"):
            filename = secure_filename(uploaded_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(filepath)
            try:
                results, counts = extract_keyword_matches(filepath, keywords, negative_keywords)
            except Exception as e:
                results = [f"❌ Error reading PDF: {str(e)}"]

    return render_template("index.html",
                           results=results,
                           keywords=keywords,
                           keyword_history=sorted(keyword_history),
                           negative_keyword_history=sorted(negative_keyword_history),
                           counts=counts)

if __name__ == "__main__":
    app.run(debug=True)
