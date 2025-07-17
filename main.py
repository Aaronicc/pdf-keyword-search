from flask import Flask, render_template, request
import PyPDF2
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Store keyword history in memory
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

            # Read PDF and search for keywords
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        lines = text.split("\n")
                        for line in lines:
                            for keyword in keywords:
                                if keyword.lower() in line.lower():
                                    results.append(f"Match: \"{line.strip()}\"")

    return render_template("index.html", results=results, keywords=keywords, history=keyword_history)
