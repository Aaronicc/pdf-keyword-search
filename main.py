import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Ensure DB exists
def init_db():
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS keywords (
                    keyword TEXT,
                    type TEXT
                )''')
    conn.commit()
    conn.close()

init_db()

def get_keywords():
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute("SELECT keyword, type FROM keywords")
    data = c.fetchall()
    conn.close()
    pos_keywords = [kw for kw, t in data if t == "positive"]
    neg_keywords = [kw for kw, t in data if t == "negative"]
    return pos_keywords, neg_keywords

def extract_keyword_matches(pdf_path, pos_keywords, neg_keywords):
    results = []
    doc = fitz.open(pdf_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()

        found_pos = [kw for kw in pos_keywords if kw.lower() in text.lower()]
        found_neg = [kw for kw in neg_keywords if kw.lower() in text.lower()]

        snippet = ""
        if found_pos or found_neg:
            keywords_combined = found_pos + found_neg
            for kw in keywords_combined:
                idx = text.lower().find(kw.lower())
                if idx != -1:
                    start = max(0, idx - 50)
                    end = min(len(text), idx + len(kw) + 50)
                    snippet = text[start:end].replace('\n', ' ')
                    break

            results.append({
                "page": page_num + 1,
                "found_positive": found_pos,
                "found_negative": found_neg,
                "snippet": snippet
            })
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    pos_keywords, neg_keywords = get_keywords()
    results = []
    if request.method == 'POST':
        file = request.files['pdf']
        if file:
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            results = extract_keyword_matches(path, pos_keywords, neg_keywords)
    return render_template('index.html', pos_keywords=pos_keywords, neg_keywords=neg_keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword'].strip().lower()
    keyword_type = request.form['type']
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute("INSERT INTO keywords (keyword, type) VALUES (?, ?)", (keyword, keyword_type))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/delete_keyword', methods=['POST'])
def delete_keyword():
    keyword = request.form['keyword'].strip().lower()
    keyword_type = request.form['type']
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute("DELETE FROM keywords WHERE keyword = ? AND type = ?", (keyword, keyword_type))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/edit_keyword', methods=['POST'])
def edit_keyword():
    original = request.form['original_keyword'].strip().lower()
    new_keyword = request.form['new_keyword'].strip().lower()
    keyword_type = request.form['type']
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute("UPDATE keywords SET keyword = ? WHERE keyword = ? AND type = ?", (new_keyword, original, keyword_type))
    conn.commit()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
