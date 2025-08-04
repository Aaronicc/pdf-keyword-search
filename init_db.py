import sqlite3

conn = sqlite3.connect('keywords.db')  # Make sure this path matches your app
c = conn.cursor()

# Create the keywords table
c.execute('''
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    type TEXT CHECK(type IN ('positive', 'negative')) NOT NULL
)
''')

conn.commit()
conn.close()
print("✅ Table 'keywords' created successfully.")
