import sqlite3

conn = sqlite3.connect("keywords.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word TEXT NOT NULL,
    type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
)
""")

conn.commit()
conn.close()
print("✅ Database initialized with `keywords` table.")
