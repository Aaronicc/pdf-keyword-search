from flask import Flask, request, render_template_string
import PyPDF2

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>PDF Keyword Search</title>
</head>
<body>
  <h1>Upload PDF & Search Keywords</h1>
  <form method="post" enctype="multipart/form-data">
    <p><input type="file" name="pdf"></p>
    <p><input type="text" name="keywords" placeholder="Enter keywords, comma-separated"></p>
    <p><button type="submit">Search</button></p>
  </form>

  {% if results %}
    <h2>Results</h2>
    <ul>
      {% for kw, pages in results.items() %}
        <li><b>{{ kw }}</b>: found on pages {{ pages }}</li>
      {% endfor %}
    </ul>
  {% endif %}
</body>
</html>
"""

def search_pdf(file_storage, keywords):
    keywords = [kw.strip().lower() for kw in keywords.split(",") if kw.strip()]
    results = {}

    # Reset file pointer for Flask uploads
    file_storage.stream.seek(0)
    reader = PyPDF2.PdfReader(file_storage.stream)

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text()
        except Exception:
            text = ""
        if text:
            lower_text = text.lower()
            for kw in keywords:
                if kw in lower_text:
                    results.setdefault(kw, []).append(page_num)

    return results

@app.route("/", methods=["GET", "POST"])
def index():
    results = None
    if request.method == "POST":
        pdf_file = request.files.get("pdf")
        keywords = request.form.get("keywords", "")
        if pdf_file and keywords:
            try:
                results = search_pdf(pdf_file, keywords)
            except Exception as e:
                results = {"error": [f"Failed to process PDF: {e}"]}
    return render_template_string(HTML_TEMPLATE, results=results)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
