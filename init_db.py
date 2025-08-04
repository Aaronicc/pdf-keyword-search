import sqlite3

conn = sqlite3.connect('keywords.db')  # Make sure the path matches your app config
c = conn.cursor()

# Create table
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
