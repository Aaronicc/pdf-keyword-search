import PyPDF2

def search_pdf(pdf_path, keywords):
    # Split keywords (strip spaces)
    keywords = [kw.strip().lower() for kw in keywords.split(",")]

    results = {kw: [] for kw in keywords}

    # Open PDF file
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)

        # Loop through pages
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()
            if text:
                lower_text = text.lower()
                for kw in keywords:
                    if kw in lower_text:
                        results[kw].append(page_num)

    return results


if __name__ == "__main__":
    pdf_file = "sample.pdf"  # <-- replace with your PDF path
    keyword_input = input("Enter keywords (comma-separated): ")
    matches = search_pdf(pdf_file, keyword_input)

    for kw, pages in matches.items():
        if pages:
            print(f"Keyword '{kw}' found on pages: {pages}")
        else:
            print(f"Keyword '{kw}' not found.")
