from flask import Flask, render_template, request, redirect, url_for
import os
import fitz  # PyMuPDF
import sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html',
                           pos_keywords=get_keywords_by_type("positive"),
                           neg_keywords=get_keywords_by_type("negative"),
                           results=None)

    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        results = []
        with fitz.open(filepath) as doc:
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                matches = []

                for keyword in pos_keywords + neg_keywords:
                    lower_text = text.lower()
                    keyword_lower = keyword.lower()
                    if keyword_lower in lower_text:
                        keyword_type = "positive" if keyword in pos_keywords else "negative"
                        count = lower_text.count(keyword_lower)

                        # Extract text snippets (context around the keyword)
                        snippets = []
                        index = 0
                        while index < len(lower_text):
                            index = lower_text.find(keyword_lower, index)
                            if index == -1:
                                break
                            start = max(0, index - 30)
                            end = min(len(text), index + len(keyword) + 30)
                            snippet = text[start:end].replace('\n', ' ')
                            snippets.append(snippet.strip())
                            index += len(keyword_lower)

                        matches.append({
                            "keyword": keyword,
                            "type": keyword_type,
                            "count": count,
                            "snippets": snippets
                        })

                if matches:
                    results.append({
                        "page": page_num,
                        "matches": matches
                    })

        return render_template('index.html',
                               pos_keywords=get_keywords_by_type("positive"),
                               neg_keywords=get_keywords_by_type("negative"),
                               results=results)
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)

