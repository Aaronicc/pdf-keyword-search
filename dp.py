import sqlite3

def init_db():
    conn = sqlite3.connect("keywords.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('positive', 'negative'))
        )
    """)
    conn.commit()
    conn.close()

def add_keyword(keyword, keyword_type):
    conn = sqlite3.connect("keywords.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO keywords (keyword, type) VALUES (?, ?)", (keyword, keyword_type))
    conn.commit()
    conn.close()

def get_keywords(keyword_type):
    conn = sqlite3.connect("keywords.db")
    cursor = conn.cursor()
    cursor.execute("SELECT keyword FROM keywords WHERE type = ?", (keyword_type,))
    keywords = [row[0] for row in cursor.fetchall()]
    conn.close()
    return keywords
