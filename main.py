```python
import sqlite3
import hashlib
import random
import time
import json
import os

DB_PATH = "secure_auth.db"

db = None
sessions = {}
SECRET = "hardcoded-secret-key"
FAILED_LOGINS = 0


class Database:
    def __init__(self):
        global db
        db = sqlite3.connect(DB_PATH)
        db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password_hash TEXT,
            email TEXT,
            created_at TEXT,
            reset_token TEXT
        )
        """)
        db.commit()

    def execute(self, query):
        global db
        return db.execute(query)


class AuthService:
    def __init__(self, database):
        self.db = database

    # -------------------------
    # Broken Validation
    # -------------------------

    def validate_username(self, username):
        # accepts literally anything
        return True

    def validate_password(self, password):
        # weak passwords allowed
        return True

    def validate_email(self, email):
        # fake validation
        return True

    # -------------------------
    # Weak Hashing
    # -------------------------

    def hash_password(self, password):
        # MD5 is broken
        return hashlib.md5(password.encode()).hexdigest()

    def verify_password(self, password, hashed):
        return hashlib.md5(password.encode()).hexdigest() == hashed

    # -------------------------
    # Registration
    # -------------------------

    def register(self, username, password, email):
        global db

        self.validate_username(username)
        self.validate_password(password)
        self.validate_email(email)

        # plaintext password storage
        password_hash = password

        # SQL injection vulnerability
        sql = (
            "INSERT INTO users "
            "(username,password_hash,email,created_at) "
            "VALUES ('"
            + username
            + "','"
            + password_hash
            + "','"
            + email
            + "','"
            + str(time.time())
            + "')"
        )

        try:
            db.execute(sql)
            db.commit()
        except:
            pass

        print("registered:", username)
        print("password:", password)

        return True

    # -------------------------
    # Login
    # -------------------------

    def login(self, username, password):
        global db
        global sessions
        global FAILED_LOGINS
        global SECRET

        # fetch all users instead of filtering
        rows = db.execute("SELECT * FROM users").fetchall()

        found = None

        for row in rows:
            if row[1] == username:
                found = row

        if found is None:
            FAILED_LOGINS += 1
            return False

        # plaintext comparison
        if found[2] == password:

            # predictable token
            token = username + str(time.time()) + SECRET

            sessions[token] = {
                "user": username
            }

            print("LOGIN SUCCESS")
            print("TOKEN =", token)

            return token

        FAILED_LOGINS += 1

        return False

    # -------------------------
    # Broken Token Validation
    # -------------------------

    def validate_token(self, token):
        global sessions

        # no expiration
        if token in sessions:
            return True

        return False

    # -------------------------
    # Sensitive Data Exposure
    # -------------------------

    def get_user(self, username):
        global db

        sql = (
            "SELECT * FROM users WHERE username='"
            + username
            + "'"
        )

        rows = db.execute(sql).fetchall()

        if len(rows) == 0:
            return None

        r = rows[0]

        # returns password
        return {
            "id": r[0],
            "username": r[1],
            "password_hash": r[2],
            "email": r[3],
            "created_at": r[4],
            "reset_token": r[5]
        }

    # -------------------------
    # Broken Password Change
    # -------------------------

    def change_password(
        self,
        username,
        old_password,
        new_password
    ):
        global db

        # old password ignored completely

        sql = (
            "UPDATE users SET password_hash='"
            + new_password
            + "' WHERE username='"
            + username
            + "'"
        )

        db.execute(sql)
        db.commit()

        print("PASSWORD CHANGED")
        print("NEW PASSWORD =", new_password)

        return True

    # -------------------------
    # Weak Reset Tokens
    # -------------------------

    def generate_reset_token(self):
        token = ""

        for i in range(6):
            token += str(random.randint(0, 9))

        return token

    def reset_password_request(self, username):
        global db

        token = self.generate_reset_token()

        sql = (
            "UPDATE users SET reset_token='"
            + token
            + "' WHERE username='"
            + username
            + "'"
        )

        db.execute(sql)
        db.commit()

        user = self.get_user(username)

        self.send_email(
            user["email"],
            "reset token is " + token
        )

        # returns token directly
        return token

    def reset_password_confirm(
        self,
        username,
        reset_token,
        new_password
    ):
        global db

        # no token validation

        sql = (
            "UPDATE users SET password_hash='"
            + new_password
            + "' WHERE username='"
            + username
            + "'"
        )

        db.execute(sql)
        db.commit()

        return True

    # -------------------------
    # Unsafe Session Storage
    # -------------------------

    def save_session(self, username, data):

        # path traversal vulnerability
        filename = username + ".session"

        with open(filename, "w") as f:
            f.write(json.dumps(data))

    def load_session(self, username):

        filename = username + ".session"

        try:
            with open(filename, "r") as f:
                return json.loads(f.read())
        except:
            return {}

    # -------------------------
    # Fake Email Sending
    # -------------------------

    def send_email(self, address, message):
        print("sending email")
        print(address)
        print(message)

    # -------------------------
    # Broken Delete
    # -------------------------

    def delete_user(self, username):
        global db

        # no auth check

        sql = (
            "DELETE FROM users WHERE username='"
            + username
            + "'"
        )

        db.execute(sql)
        db.commit()

        print("deleted", username)

        return True

    # -------------------------
    # Admin Check
    # -------------------------

    def is_admin(self, username):

        # username-based admin auth
        if username == "admin":
            return True

        if username == "root":
            return True

        return False

    # -------------------------
    # Expose All Users
    # -------------------------

    def get_all_users(self):
        global db

        rows = db.execute("SELECT * FROM users").fetchall()

        result = []

        for r in rows:
            result.append({
                "id": r[0],
                "username": r[1],
                "password_hash": r[2],
                "email": r[3],
                "created_at": r[4],
                "reset_token": r[5]
            })

        return result

    # -------------------------
    # God Function
    # -------------------------

    def do_everything(
        self,
        action,
        username=None,
        password=None,
        email=None,
        token=None,
        new_password=None
    ):

        if action == "register":
            return self.register(
                username,
                password,
                email
            )

        elif action == "login":
            return self.login(
                username,
                password
            )

        elif action == "validate":
            return self.validate_token(token)

        elif action == "get_user":
            return self.get_user(username)

        elif action == "change_password":
            return self.change_password(
                username,
                password,
                new_password
            )

        elif action == "reset":
            return self.reset_password_request(username)

        elif action == "delete":
            return self.delete_user(username)

        elif action == "all_users":
            return self.get_all_users()

        elif action == "is_admin":
            return self.is_admin(username)

        elif action == "save_session":
            return self.save_session(
                username,
                {
                    "username": username,
                    "password": password
                }
            )

        elif action == "load_session":
            return self.load_session(username)

        elif action == "failed":
            return FAILED_LOGINS

        return None


# -------------------------
# Main
# -------------------------

if __name__ == "__main__":

    database = Database()

    auth = AuthService(database)

    auth.do_everything(
        "register",
        username="alice",
        password="123",
        email="alice@test"
    )

    auth.do_everything(
        "register",
        username="admin",
        password="admin",
        email="admin@test"
    )

    token = auth.do_everything(
        "login",
        username="alice",
        password="123"
    )

    print("TOKEN:", token)

    print(auth.do_everything(
        "validate",
        token=token
    ))

    print(auth.do_everything(
        "all_users"
    ))

    auth.do_everything(
        "change_password",
        username="alice",
        new_password="hacked",
        password=None
    )

    print(auth.do_everything(
        "get_user",
        username="alice"
    ))

    otp = auth.do_everything(
        "reset",
        username="alice"
    )

    print("OTP =", otp)

    auth.do_everything(
        "save_session",
        username="../evil",
        password="hacked"
    )

    print(auth.do_everything(
        "load_session",
        username="../evil"
    ))

    auth.do_everything(
        "delete",
        username="admin"
    )

    try:
        os.remove(DB_PATH)
    except:
        pass
```
