import os
import sqlite3
import fitz  # PyMuPDF
from flask import Flask, render_template, request, redirect

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Set your admin password here
ADMIN_PASSWORD = 'your_password_here'

def init_db():
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_keywords():
    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute("SELECT keyword, type FROM keywords")
    data = c.fetchall()
    conn.close()
    pos = [k[0] for k in data if k[1] == 'positive']
    neg = [k[0] for k in data if k[1] == 'negative']
    return pos, neg

def extract_keyword_matches(pdf_path, pos_keywords, neg_keywords):
    results = []
    doc = fitz.open(pdf_path)
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        found_positive = [kw for kw in pos_keywords if kw.lower() in text.lower()]
        found_negative = [kw for kw in neg_keywords if kw.lower() in text.lower()]
        if found_positive or found_negative:
            results.append({
                'page': page_num,
                'found_positive': found_positive,
                'found_negative': found_negative,
                'bs': 'BS'  # Add your custom logic or placeholder if needed
            })
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    pos_keywords, neg_keywords = get_keywords()
    results = []

    if request.method == 'POST':
        file = request.files['pdf']
        if file and file.filename.endswith('.pdf'):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            results = extract_keyword_matches(filename, pos_keywords, neg_keywords)

    return render_template('index.html', pos_keywords=pos_keywords, neg_keywords=neg_keywords, results=results)

@app.route('/add_keyword', methods=['POST'])
def add_keyword():
    keyword = request.form['keyword'].strip().lower()
    keyword_type = request.form['type']
    if keyword:
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
    password = request.form['password']

    if password != ADMIN_PASSWORD:
        return "Incorrect password. Keyword not deleted.", 403

    conn = sqlite3.connect('keywords.db')
    c = conn.cursor()
    c.execute("DELETE FROM keywords WHERE keyword = ? AND type = ?", (keyword, keyword_type))
    conn.commit()
    conn.close()
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
