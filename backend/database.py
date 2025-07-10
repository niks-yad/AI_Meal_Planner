import sqlite3
import json

DATABASE_URL = "temp_grocery_list.db"

def create_table():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grocery_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            list_data TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def insert_grocery_list(session_id: str, grocery_list: list):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    list_data_json = json.dumps(grocery_list)
    cursor.execute("INSERT INTO grocery_lists (session_id, list_data) VALUES (?, ?)", (session_id, list_data_json))
    conn.commit()
    conn.close()

def get_grocery_list(session_id: str):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT list_data FROM grocery_lists WHERE session_id = ?", (session_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return json.loads(result[0])
    return None

def delete_grocery_list(session_id: str):
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM grocery_lists WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()

# Ensure the table is created when the module is imported
create_table()
