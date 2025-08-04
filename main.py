import os
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# In-memory keyword storage
positive_keywords = set()
negative_keywords = set()
ADMIN_PASSWORD = "admin123"  # Change this securely

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    summary_count = {'positive': {}, 'negative': {}}
    error = None

    if request.method == 'POST' and 'pdf' in request.files:
        pdf_file = request.files['pdf']
        if pdf_file.filename.endswith('.pdf'):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(pdf_file.filename))
            pdf_file.save(filepath)

            with fitz.open(filepath) as doc:
                for page_num, page in enumerate(doc, start=1):
                    text = page.get_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    matched_lines = []
                    found_positive = set()
                    found_negative = set()

                    for line in lines:
                        lower_line = line.lower()
                        matched = False
                        for kw in positive_keywords:
                            if kw.lower() in lower_line:
                                found_positive.add(kw)
                                matched = True
                        for kw in negative_keywords:
                            if kw.lower() in lower_line:
                                found_negative.add(kw)
                                matched = True
                        if matched:
                            matched_lines.append(line)

                    if matched_lines:
                        for kw in found_positive:
                            summary_count['positive'][kw] = summary_count['positive'].get(kw, 0) + 1
                        for kw in found_negative:
                            summary_count['negative'][kw] = summary_count['negative'].get(kw, 0) + 1

                        results.append({
                            'page': page_num,
                            'lines': matched_lines,
                            'found_positive': list(found_positive),
                            'found_negative': list(found_negative)
                        })

    return render_template('index.html',
                           pos_keywords=sorted(positive_keywords),
                           neg_keywords=sorted(negative_keywords),
                           results=results,
                           summary_count=summary_count if results else None,
                           error=error)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword'].strip()
    kw_type = request.form['type']
    password = request.form['password']
    error = None

    if password != ADMIN_PASSWORD:
        error = "Incorrect password."
    elif keyword.lower() in [k.lower() for k in positive_keywords.union(negative_keywords)]:
        error = "Keyword already exists."
    else:
        if kw_type == 'positive':
            positive_keywords.add(keyword)
        elif kw_type == 'negative':
            negative_keywords.add(keyword)

    return redirect(url_for('index', error=error))

@app.route('/delete_keyword/<keyword>', methods=['POST'])
def delete_keyword(keyword):
    password = request.form.get('password')
    if password == ADMIN_PASSWORD:
        positive_keywords.discard(keyword)
        negative_keywords.discard(keyword)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
