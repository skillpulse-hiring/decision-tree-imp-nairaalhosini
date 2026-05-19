import sqlite3
import bcrypt
import secrets
import json
import time
from pathlib import Path
from typing import Optional

DB_PATH = "secure_auth.db"
SESSION_DIR = Path("sessions")

SESSION_DIR.mkdir(exist_ok=True)


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            reset_token TEXT
        )
        """)

        self.conn.commit()

    def execute(self, query, params=()):
        cursor = self.conn.execute(query, params)
        self.conn.commit()
        return cursor


class AuthService:
    def __init__(self, db: Database):
        self.db = db
        self.sessions = {}

    # -------------------------
    # Validation
    # -------------------------

    def validate_username(self, username: str):
        if not username:
            raise ValueError("Username required")

        if len(username) < 3:
            raise ValueError("Username too short")

    def validate_password(self, password: str):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

    def validate_email(self, email: str):
        if "@" not in email:
            raise ValueError("Invalid email")

    # -------------------------
    # Password Hashing
    # -------------------------

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    # -------------------------
    # Registration
    # -------------------------

    def register(self, username: str, password: str, email: str):
        self.validate_username(username)
        self.validate_password(password)
        self.validate_email(email)

        existing = self.db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            raise ValueError("Username already exists")

        password_hash = self.hash_password(password)

        self.db.execute("""
            INSERT INTO users (
                username,
                password_hash,
                email,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            username,
            password_hash,
            email,
            str(time.time())
        ))

        return {
            "success": True,
            "message": "User registered"
        }

    # -------------------------
    # Login
    # -------------------------

    def login(self, username: str, password: str) -> str:
        user = self.db.execute("""
            SELECT * FROM users WHERE username = ?
        """, (username,)).fetchone()

        if not user:
            raise ValueError("Invalid credentials")

        if not self.verify_password(password, user["password_hash"]):
            raise ValueError("Invalid credentials")

        token = secrets.token_hex(32)

        self.sessions[token] = {
            "username": username,
            "created_at": time.time(),
            "expires_at": time.time() + 3600
        }

        return token

    # -------------------------
    # Token Validation
    # -------------------------

    def validate_token(self, token: str) -> bool:
        session = self.sessions.get(token)

        if not session:
            return False

        if session["expires_at"] < time.time():
            del self.sessions[token]
            return False

        return True

    # -------------------------
    # Get User
    # -------------------------

    def get_user(self, username: str):
        user = self.db.execute("""
            SELECT id, username, email, created_at
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if not user:
            return None

        return dict(user)

    # -------------------------
    # Change Password
    # -------------------------

    def change_password(
        self,
        username: str,
        old_password: str,
        new_password: str
    ):
        self.validate_password(new_password)

        user = self.db.execute("""
            SELECT * FROM users WHERE username = ?
        """, (username,)).fetchone()

        if not user:
            raise ValueError("User not found")

        if not self.verify_password(
            old_password,
            user["password_hash"]
        ):
            raise ValueError("Old password incorrect")

        new_hash = self.hash_password(new_password)

        self.db.execute("""
            UPDATE users
            SET password_hash = ?
            WHERE username = ?
        """, (
            new_hash,
            username
        ))

        return {
            "success": True
        }

    # -------------------------
    # Password Reset
    # -------------------------

    def generate_reset_token(self):
        return secrets.token_urlsafe(32)

    def reset_password_request(self, username: str):
        user = self.db.execute("""
            SELECT * FROM users WHERE username = ?
        """, (username,)).fetchone()

        if not user:
            raise ValueError("User not found")

        token = self.generate_reset_token()

        self.db.execute("""
            UPDATE users
            SET reset_token = ?
            WHERE username = ?
        """, (
            token,
            username
        ))

        self.send_email(
            user["email"],
            f"Password reset token: {token}"
        )

        return {
            "success": True
        }

    def reset_password_confirm(
        self,
        username: str,
        reset_token: str,
        new_password: str
    ):
        self.validate_password(new_password)

        user = self.db.execute("""
            SELECT * FROM users
            WHERE username = ?
              AND reset_token = ?
        """, (
            username,
            reset_token
        )).fetchone()

        if not user:
            raise ValueError("Invalid reset token")

        new_hash = self.hash_password(new_password)

        self.db.execute("""
            UPDATE users
            SET password_hash = ?,
                reset_token = NULL
            WHERE username = ?
        """, (
            new_hash,
            username
        ))

        return {
            "success": True
        }

    # -------------------------
    # Session Storage
    # -------------------------

    def save_session(self, username: str, data: dict):
        safe_name = username.replace("/", "_")

        path = SESSION_DIR / f"{safe_name}.json"

        sanitized = {
            "username": username,
            "last_login": data.get("last_login")
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(sanitized, f)

    def load_session(self, username: str):
        safe_name = username.replace("/", "_")

        path = SESSION_DIR / f"{safe_name}.json"

        if not path.exists():
            return {}

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # -------------------------
    # Email
    # -------------------------

    def send_email(self, address: str, message: str):
        # Replace with real SMTP provider
        print(f"Email sent to {address}")

    # -------------------------
    # Delete User
    # -------------------------

    def delete_user(self, username: str):
        self.db.execute("""
            DELETE FROM users
            WHERE username = ?
        """, (username,))

        return {
            "success": True
        }


# -------------------------
# Main
# -------------------------

if __name__ == "__main__":
    db = Database()
    auth = AuthService(db)

    try:
        auth.register(
            "alice",
            "StrongPassword123!",
            "alice@example.com"
        )

        token = auth.login(
            "alice",
            "StrongPassword123!"
        )

        print("Session token generated")

        print(auth.validate_token(token))

        print(auth.get_user("alice"))

        auth.change_password(
            "alice",
            "StrongPassword123!",
            "NewStrongPassword456!"
        )

        auth.reset_password_request("alice")

    except Exception as e:
        print("Error:", str(e))
