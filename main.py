import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Use SQLite for storage
db_url = "sqlite:///keywords.db"
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Example model
class Keyword(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(10))  # "positive" or "negative"

with app.app_context():
    db.create_all()

# ----------------------------------
# OCR Helpers
# ----------------------------------
def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using OCR."""
    images = convert_from_path(pdf_path)
    text = ""
    for img in images:
        text += pytesseract.image_to_string(img) + "\n"
    return text

def extract_text_from_image(image_path):
    """Extract text from a single image."""
    img = Image.open(image_path)
    return pytesseract.image_to_string(img)

# ----------------------------------
# Routes
# ----------------------------------
@app.route("/")
def index():
    keywords = Keyword.query.all()
    return render_template("index.html", keywords=keywords)

@app.route("/add_keyword", methods=["POST"])
def add_keyword():
    word = request.form.get("word")
    ktype = request.form.get("type")
    if not word:
        flash("Keyword cannot be empty!", "danger")
        return redirect(url_for("index"))

    try:
        db.session.add(Keyword(word=word.strip(), type=ktype))
        db.session.commit()
        flash("Keyword added successfully!", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Keyword already exists!", "danger")

    return redirect(url_for("index"))

@app.route("/delete_keyword/<int:id>", methods=["POST"])
def delete_keyword(id):
    keyword = Keyword.query.get_or_404(id)
    db.session.delete(keyword)
    db.session.commit()
    flash("Keyword deleted!", "success")
    return redirect(url_for("index"))

@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        flash("No file part", "danger")
        return redirect(url_for("index"))

    files = request.files.getlist("files")
    if not files or files[0].filename == "":
        flash("No selected files", "danger")
        return redirect(url_for("index"))

    all_text = ""
    upload_folder = "uploads"
    os.makedirs(upload_folder, exist_ok=True)

    for file in files:
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        if filename.lower().endswith(".pdf"):
            all_text += extract_text_from_pdf(filepath)
        else:
            all_text += extract_text_from_image(filepath)

    # Search keywords
    results = []
    keywords = Keyword.query.all()
    for keyword in keywords:
        if keyword.word.lower() in all_text.lower():
            results.append({"word": keyword.word, "type": keyword.type})

    return render_template("results.html", results=results, text=all_text)

# ----------------------------------
# Run
# ----------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
