from flask import Flask, request, render_template
import os, json, PyPDF2

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
KEYWORDS_FILE = "keywords.json"
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
    results, previous = [], load_keywords()
    if request.method == "POST":
        file = request.files.get("pdf")
        keywords = [k.strip() for k in request.form["keywords"].lower().split(",") if k.strip()]
        save_keywords(keywords)
        if file and file.filename.lower().endswith(".pdf"):
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            try:
                reader = PyPDF2.PdfReader(open(path, "rb"))
                for i, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text:
                        for line in text.split("\n"):
                            matches = [kw for kw in keywords if kw in line.lower()]
                            if matches:
                                results.append({"page":i+1,"text":line.strip(),"matched":", ".join(matches)})
            except PyPDF2.errors.PdfReadError:
                results.append({"page":"N/A","text":"❌ Could not read PDF.","matched":""})
    return render_template("index.html", results=results, previous_keywords=previous)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
