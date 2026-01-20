import sqlite3
from pathlib import Path

DB_FILE = Path("users.db")

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                message_id INTEGER,
                winner_id INTEGER,
                timestamp REAL,
                PRIMARY KEY (message_id, winner_id),
                FOREIGN KEY(winner_id) REFERENCES users(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS state (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.commit()

def add_user(user_id, username: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()

def get_users():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, id FROM users")
        return cursor.fetchall()

def log_win(message_id, winner_id, timestamp):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        # Ahora esto funcionará para múltiples ganadores en el mismo mensaje
        cursor.execute("INSERT OR IGNORE INTO results (message_id, winner_id, timestamp) VALUES (?, ?, ?)", 
                       (message_id, winner_id, timestamp))
        conn.commit()

def get_total_scores():
    """Devuelve [(id, username, wins), ...] ordenado por victorias."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        query = """
            SELECT u.id, u.username, COUNT(r.winner_id) as wins
            FROM users u
            LEFT JOIN results r ON u.id = r.winner_id
            GROUP BY u.id
            HAVING wins > 0
            ORDER BY wins DESC
        """
        cursor.execute(query)
        return cursor.fetchall()

def get_last_processed_id():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM state WHERE key = 'last_msg_id'")
        row = cursor.fetchone()
        return int(row[0]) if row else None

def set_last_processed_id(msg_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('last_msg_id', ?)", (str(msg_id),))
        conn.commit()
