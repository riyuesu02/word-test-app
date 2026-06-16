import sqlite3

conn = sqlite3.connect("word_test.db")

rows = conn.execute(
    "SELECT * FROM results LIMIT 10"
).fetchall()

for r in rows:
    print(r)

conn.close()