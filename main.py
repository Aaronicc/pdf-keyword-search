from flask import Flask, render_template, request
import PyPDF2
import os
import json

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
KEYWORDS_FILE = "keywords.json"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(KEYWORDS_FILE):
    with open(KEYWORDS_FILE, "w") as f:
        json.dump([], f)

def search_keywords_in_pdf(pdf_path, keywords):
    results = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                for keyword in keywords:
                    if keyword.lower() in text.lower():
                        results.append(f"Found '{keyword}' on page {page_num + 1}")
    return results

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    previous_keywords = []
    if os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, "r") as f:
            previous_keywords = json.load(f)

    if request.method == "POST":
        uploaded_file = request.files["pdf"]
        keywords = request.form["keywords"].split(",")
        keywords = [k.strip() for k in keywords if k.strip()]

        if uploaded_file.filename != "":
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], uploaded_file.filename)
            uploaded_file.save(file_path)
            results = search_keywords_in_pdf(file_path, keywords)

            all_keywords = list(set(previous_keywords + keywords))
            with open(KEYWORDS_FILE, "w") as f:
                json.dump(all_keywords, f)

    return render_template("index.html", results=results, previous_keywords=previous_keywords)

if __name__ == "__main__":
    app.run(debug=True)
