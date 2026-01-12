"""
storage.py

Functions to work with the database. Database will store the usernames and the º
"""
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
        conn.commit()

def add_user(user_id, username: str):
    """
    Adds a user to the database, so that its results will be logged
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()

def get_users():
    """
    Gets the list of users
    """
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, id FROM users")
        rows = cursor.fetchall()
    return rows

