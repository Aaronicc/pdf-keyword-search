from flask import Flask, render_template, request
import PyPDF2
import os
import re

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Store keyword history
keyword_history = []

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    keywords = []

    if request.method == "POST":
        uploaded_file = request.files["pdf_file"]
        raw_keywords = request.form["keywords"]

        if uploaded_file and raw_keywords:
            keywords = [kw.strip() for kw in raw_keywords.split(",") if kw.strip()]
            keyword_history.extend([kw for kw in keywords if kw not in keyword_history])

            pdf_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(pdf_path)

            # PDF reading
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        lines = text.split("\n")
                        for line in lines:
                            for keyword in keywords:
                                if keyword.lower() in line.lower():
                                    highlighted_line = re.sub(
                                        f"({re.escape(keyword)})",
                                        r"<mark>\1</mark>",
                                        line,
                                        flags=re.IGNORECASE,
                                    )
                                    results.append(f"<strong>Page {page_num + 1}</strong>: {highlighted_line}")
                                    break  # Avoid repeating if multiple keywords hit in one line

    return render_template("index.html", results=results, keywords=keywords, history=keyword_history)
