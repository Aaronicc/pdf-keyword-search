from flask import Flask, request, render_template
import os
import json
import PyPDF2

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
KEYWORDS_FILE = "keywords.json"

# Ensure upload and keyword file exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
if not os.path.exists(KEYWORDS_FILE):
    with open(KEYWORDS_FILE, "w") as f:
        json.dump([], f)

def load_keywords():
    with open(KEYWORDS_FILE, "r") as f:
        return json.load(f)

def save_keywords(new_keywords):
    with open(KEYWORDS_FILE, "w") as f:
        json.dump(new_keywords, f)

@app.route("/", methods=["GET", "POST"])
def index():
    results = []
    previous_keywords = load_keywords()

    if request.method == "POST":
        file = request.files["pdf"]
        keywords = request.form["keywords"].lower().split(",")
        keywords = [k.strip() for k in keywords if k.strip()]
        save_keywords(keywords)

        if file and file.filename.endswith(".pdf"):
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            try:
                with open(path, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for i, page in enumerate(reader.pages):
                        text = page.extract_text()
                        if text:
                            for line in text.split("\n"):
                                matches = [kw for kw in keywords if kw in line.lower()]
                                if matches:
                                    results.append({
                                        "page": i + 1,
                                        "text": line.strip(),
                                        "matched": ", ".join(matches)
                                    })
            except PyPDF2.errors.PdfReadError:
                results.append({
                    "page": "N/A",
                    "text": "❌ Could not read this PDF. It may be damaged or scanned.",
                    "matched": ""
                })
            except Exception as e:
                results.append({
                    "page": "N/A",
                    "text": f"❌ Unexpected error: {str(e)}",
                    "matched": ""
                })

    return render_template("index.html", results=results, previous_keywords=previous_keywords)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
