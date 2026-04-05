import sqlite3

conn = sqlite3.connect("database.db")
conn.row_factory = sqlite3.Row

print("Search History:")
for r in conn.execute("SELECT id, user_id, medicine_name FROM search_history"):
    print(dict(r))

print("\nUsers:")
for u in conn.execute("SELECT id, name FROM users"):
    print(dict(u))

conn.close()
