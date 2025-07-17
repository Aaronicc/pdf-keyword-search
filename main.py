from flask import Flask, render_template, request
import os
import PyPDF2

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
KEYWORDS_FILE = 'keywords.txt'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def save_keywords(keywords):
    try:
        with open("keywords.json", "r") as f:
            existing = json.load(f)
    except FileNotFoundError:
        existing = []

    for kw in keywords:
        if kw not in existing:
            existing.append(kw)

    with open("keywords.json", "w") as f:
        json.dump(existing, f)

def load_keywords():
    try:
        with open("keywords.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    with open(KEYWORDS_FILE, "r") as f:
        return [kw.strip() for kw in f.readlines()]

def search_pdf_lines(pdf_path, keywords):
    results = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                lines = text.splitlines()
                for line in lines:
                    matched_keywords = [kw for kw in keywords if kw.lower() in line.lower()]
                    if matched_keywords:
                        results.append({
                            "page": page_num + 1,
                            "line": line.strip(),
                            "keywords": matched_keywords
                        })
    return results

@app.route("/", methods=["GET", "POST"])
def index():
    result = []
    previous_keywords = load_keywords()

    if request.method == "POST":
        uploaded_file = request.files["pdf_file"]
        keywords = request.form["keywords"].split(",")
        keywords = [kw.strip() for kw in keywords if kw.strip()]
        save_keywords(keywords)

        # Save PDF
        if not os.path.exists("uploads"):
            os.makedirs("uploads")
        file_path = os.path.join("uploads", uploaded_file.filename)
        uploaded_file.save(file_path)

        # Search in PDF
        result = search_keywords_in_pdf(file_path, keywords)

    return render_template("index.html", results=result, previous_keywords=previous_keywords)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
