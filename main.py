from flask import Flask, render_template, request
import os
import PyPDF2

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    results = []
    if request.method == "POST":
        uploaded_file = request.files.get("pdf")
        keywords_input = request.form.get("keywords", "")
        keywords = [kw.strip() for kw in keywords_input.split(",") if kw.strip()]
        print("Parsed Keywords:", keywords)

        if uploaded_file and uploaded_file.filename:
            file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(file_path)
            results = search_pdf_lines(file_path, keywords)

    return render_template("index.html", results=results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
